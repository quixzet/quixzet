import express from 'express';
import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {fileURLToPath} from 'node:url';
import {routes} from './routes.js';
import {render} from './templates.js';

const backend = new URL(process.env.BACKEND_URL || 'http://127.0.0.1:8000');
const app = express();
app.disable('x-powered-by');
app.use('/assets', express.static(fileURLToPath(new URL('./public', import.meta.url)), {
    dotfiles: 'ignore',
    index: false,
}));

function fetchBackend(req, path) {
    const headers = new Headers();
    for (const name of ['cookie', 'content-type', 'origin', 'referer', 'range', 'if-modified-since', 'if-none-match']) {
        if (req.headers[name]) headers.set(name, req.headers[name]);
    }
    const target = new URL(backend);
    const url = new URL(path, 'http://storefront.local');
    target.pathname = url.pathname;
    target.search = url.search;
    return fetch(target, {
        method: req.method,
        headers,
        body: req.method === 'POST' ? req.body : undefined,
        redirect: 'manual',
        signal: AbortSignal.timeout(30_000),
    });
}

function copyCookies(res, upstream) {
    for (const cookie of upstream.headers.getSetCookie()) {
        res.append('Set-Cookie', cookie);
    }
}

app.use('/media', async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') return res.sendStatus(405);
    const upstream = await fetchBackend(req, req.originalUrl);
    for (const name of ['content-type', 'content-range', 'accept-ranges', 'last-modified', 'etag', 'cache-control']) {
        const value = upstream.headers.get(name);
        if (value) res.set(name, value);
    }
    res.set('X-Content-Type-Options', 'nosniff');
    res.set('Content-Security-Policy', "default-src 'none'; sandbox");
    res.status(upstream.status);
    if (upstream.body) return pipeline(Readable.fromWeb(upstream.body), res);
    res.end();
});

function page(req, res, template, data, status) {
    res.set('Cache-Control', 'private, no-store');
    res.status(status).send(render(template, {...data, path: req.path, fullPath: req.originalUrl}));
}

const parseBody = express.raw({type: '*/*', limit: '12mb'});
const fileNotFound = (req, res) => page(req, res, '404.html', {}, 404);

function storefrontLocation(location) {
    const redirect = new URL(location, backend);
    if (redirect.origin !== backend.origin) throw new Error('Unexpected backend redirect');
    const path = redirect.pathname.replace(/^\/api(?=\/)/, '');
    if (path.startsWith('//')) throw new Error('Unexpected redirect path');
    return path + redirect.search + redirect.hash;
}

for (const [route, path, template] of routes) {
    const handle = async (req, res) => {
        const incoming = new URL(req.originalUrl, 'http://storefront.local');
        if (!incoming.pathname.endsWith('/')) incoming.pathname += '/';
        const upstream = await fetchBackend(req, '/api' + incoming.pathname + incoming.search);
        copyCookies(res, upstream);
        const location = upstream.headers.get('location');
        if (location && upstream.status >= 300 && upstream.status < 400) {
            await upstream.body?.cancel();
            res.set('Cache-Control', 'private, no-store');
            return res.redirect(req.method === 'POST' ? 303 : 302, storefrontLocation(location));
        }
        if (upstream.status === 404) {
            await upstream.body?.cancel();
            return fileNotFound(req, res);
        }
        if (!upstream.headers.get('content-type')?.startsWith('application/json')) {
            await upstream.body?.cancel();
            return res.sendStatus(upstream.ok ? 502 : upstream.status);
        }
        const data = await upstream.json();
        if (!template || data.error) {
            return res.status(upstream.status).type('text/plain').send(data.error || 'Действие недоступно');
        }
        return page(req, res, template, {...data, route}, upstream.status);
    };
    if (template) app.get(path, handle);
    app.post(path, parseBody, handle);
}

app.use(fileNotFound);
app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    console.error(error);
    res.status(error.status || 502).type('text/plain').send('Не удалось обработать запрос.');
});

app.listen(Number(process.env.PORT || 3000), process.env.HOST || '127.0.0.1');
