const tg = window.Telegram.WebApp;
tg.ready();

const form = document.getElementById('bookingForm');
const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const errorDiv = document.getElementById('formError');
const progressBar = document.getElementById('progressBar');
const progressFill = progressBar.querySelector('.progress-fill');
const totalPriceSpan = document.getElementById('totalPrice');
const serviceSelect = document.getElementById('serviceSelect');
let flatpickrInstance = null;

function updatePrice() {
    const selected = serviceSelect.options[serviceSelect.selectedIndex];
    const price = selected.getAttribute('data-price') || 0;
    totalPriceSpan.textContent = 'Стоимость: ' + price + ' ₽';
}
serviceSelect.addEventListener('change', updatePrice);
updatePrice();

function initFlatpickr() {
    const datetimeInput = document.getElementById('datetimePicker');
    if (!datetimeInput) return;
    flatpickrInstance = flatpickr(datetimeInput, {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        minuteIncrement: 30,
        minDate: "today",
        locale: "ru",
        onChange: function() { saveFormData(); }
    });
}

function saveFormData() {
    const data = {
        name: form.name.value,
        phone: form.phone.value,
        service: form.service.value,
        master: form.master.value,
        datetime: form.datetime.value
    };
    localStorage.setItem('beautybook_form', JSON.stringify(data));
}

function loadSavedData() {
    const saved = localStorage.getItem('beautybook_form');
    if (saved) {
        const data = JSON.parse(saved);
        form.name.value = data.name || '';
        form.phone.value = data.phone || '';
        form.service.value = data.service || '💅 Маникюр';
        form.master.value = data.master || '👩‍🦰 Анна';
        if (data.datetime && flatpickrInstance) flatpickrInstance.setDate(data.datetime, false);
        updatePrice();
    }
}

function validateForm() {
    const name = form.name.value.trim();
    const phone = form.phone.value.trim();
    const datetime = form.datetime.value;
    if (!name) return "Введите имя";
    if (!phone) return "Введите телефон";
    const phoneRegex = /^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$/;
    if (!phoneRegex.test(phone)) return "Некорректный номер телефона";
    if (!datetime) return "Выберите дату и время";
    const selected = new Date(datetime);
    const now = new Date();
    if (selected < now) return "Дата не может быть в прошлом";
    return null;
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = validateForm();
    if (err) {
        errorDiv.textContent = err;
        errorDiv.style.display = 'block';
        return;
    }
    errorDiv.style.display = 'none';
    progressBar.style.display = 'block';
    progressFill.style.width = '0%';
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Отправка...';

    let width = 0;
    const interval = setInterval(() => {
        if (width >= 90) clearInterval(interval);
        else {
            width += 10;
            progressFill.style.width = width + '%';
        }
    }, 100);

    const formData = {
        name: form.name.value.trim(),
        phone: form.phone.value.trim(),
        service: form.service.value,
        master: form.master.value,
        datetime: form.datetime.value
    };
    try {
        tg.sendData(JSON.stringify(formData));
        clearInterval(interval);
        progressFill.style.width = '100%';
        setTimeout(() => tg.close(), 1500);
    } catch (err) {
        console.error(err);
        clearInterval(interval);
        progressBar.style.display = 'none';
        errorDiv.textContent = 'Ошибка отправки. Попробуйте позже.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = '✅ Записаться';
    }
});

resetBtn.addEventListener('click', () => {
    form.reset();
    localStorage.removeItem('beautybook_form');
    errorDiv.style.display = 'none';
    progressBar.style.display = 'none';
    if (flatpickrInstance) flatpickrInstance.clear();
    updatePrice();
});

form.addEventListener('input', saveFormData);

document.addEventListener('DOMContentLoaded', () => {
    initFlatpickr();
    loadSavedData();
    tg.expand();
});
