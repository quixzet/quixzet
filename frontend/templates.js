import nunjucks from 'nunjucks';
import {fileURLToPath} from 'node:url';
import {formFields} from './forms.js';
import {url} from './routes.js';

const templates = new nunjucks.Environment(
    new nunjucks.FileSystemLoader(fileURLToPath(new URL('./templates', import.meta.url))),
    {autoescape: true},
);

const money = new Intl.NumberFormat('ru-RU', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const dateParts = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Europe/Moscow', dateStyle: 'short', timeStyle: 'short',
});
const plurals = new Intl.PluralRules('ru-RU');

templates.addFilter('rub', value => {
    if (value == null || value === '') return '';
    return money.format(value).replace(/,00$/, '').replace(/^-/, '−') + '\u00a0₽';
});
templates.addFilter('discount', (price, old) => Number(old) > Number(price) ? Math.round((1 - price / old) * 100) : '');
templates.addFilter('pad', (value, width = 3) => String(value).padStart(width, '0'));
templates.addFilter('add', (value, amount) => Number(value) + Number(amount));
templates.addFilter('number', Number);
templates.addFilter('substring', (value, bounds) => {
    const [start, end] = bounds.split(':');
    return String(value).slice(Number(start), end ? Number(end) : undefined);
});
templates.addFilter('plural', (value, forms) => {
    const [one, few, many] = forms.split(',');
    return {one, few, many}[plurals.select(Number(value))] || many;
});
templates.addFilter('date', (value, format) => {
    if (!value) return '';
    const formatted = dateParts.format(new Date(value));
    const [year, month, day, hours, minutes] = formatted.match(/\d+/g);
    return format.replace(/[YmdHi]/g, token => ({Y: year, m: month, d: day, H: hours, i: minutes})[token]);
});
templates.addFilter('linebreaks', value => {
    const escaped = String(templates.getFilter('escape')(value));
    const paragraphs = escaped.replace(/\r\n?/g, '\n').split(/\n{2,}/);
    return new nunjucks.runtime.SafeString(paragraphs.map(p => '<p>' + p.replaceAll('\n', '<br>') + '</p>').join(''));
});
templates.addGlobal('url', url);
templates.addGlobal('now', () => new Date());
templates.addGlobal('formFields', formFields);
templates.addGlobal('orderSteps', status => {
    const current = {new: 0, awaiting_payment: 0, paid: 1, shipped: 2, delivered: 3}[status];
    if (current === undefined) return [];
    return ['оформлен', 'оплачен', 'в пути', 'доставлен'].map((label, index) => ({
        label, done: index <= current, current: index === current,
    }));
});

export function render(template, data) {
    return templates.render(template, {
        ...data,
        selected_variant: data.variants?.find(variant => variant.id === data.selected_variant_id),
        is_edit: data.route === 'profile-address-edit',
    });
}
