const tg = window.Telegram.WebApp;
tg.ready();

const form = document.getElementById('bookingForm');
const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const errorDiv = document.getElementById('formError');
const successDiv = document.getElementById('formSuccess');

// Загрузка сохранённых данных из localStorage
function loadSavedData() {
    const saved = localStorage.getItem('beautybook_form');
    if (saved) {
        const data = JSON.parse(saved);
        for (const [key, value] of Object.entries(data)) {
            const input = form.elements[key];
            if (input) input.value = value;
        }
    }
}

// Сохранение данных в localStorage
function saveFormData() {
    const data = {};
    for (let i = 0; i < form.elements.length; i++) {
        const el = form.elements[i];
        if (el.name) data[el.name] = el.value;
    }
    localStorage.setItem('beautybook_form', JSON.stringify(data));
}

// Валидация формы
function validateForm() {
    const name = form.name.value.trim();
    const phone = form.phone.value.trim();
    const datetime = form.datetime.value;

    if (!name) {
        errorDiv.textContent = 'Пожалуйста, введите имя';
        errorDiv.style.display = 'block';
        return false;
    }
    if (!phone) {
        errorDiv.textContent = 'Пожалуйста, введите номер телефона';
        errorDiv.style.display = 'block';
        return false;
    }
    const phoneRegex = /^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$/;
    if (!phoneRegex.test(phone)) {
        errorDiv.textContent = 'Введите корректный номер телефона (например, +7 123 456-78-90)';
        errorDiv.style.display = 'block';
        return false;
    }
    if (!datetime) {
        errorDiv.textContent = 'Выберите дату и время';
        errorDiv.style.display = 'block';
        return false;
    }
    const selected = new Date(datetime);
    const now = new Date();
    if (selected < now) {
        errorDiv.textContent = 'Дата и время не могут быть в прошлом';
        errorDiv.style.display = 'block';
        return false;
    }
    errorDiv.style.display = 'none';
    return true;
}

// Отправка формы
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    saveFormData();

    const formData = {
        name: form.name.value.trim(),
        phone: form.phone.value.trim(),
        service: form.service.value,
        master: form.master.value,
        datetime: form.datetime.value
    };

    submitBtn.disabled = true;
    submitBtn.textContent = '📤 Отправка...';

    try {
        tg.sendData(JSON.stringify(formData));
        successDiv.style.display = 'block';
        successDiv.textContent = '✅ Заявка отправлена! Приложение закроется...';
        setTimeout(() => {
            tg.close();
        }, 1500);
    } catch (err) {
        console.error(err);
        errorDiv.textContent = 'Ошибка отправки. Попробуйте позже.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = '✅ Записаться';
    }
});

// Кнопка сброса формы
resetBtn.addEventListener('click', () => {
    form.reset();
    localStorage.removeItem('beautybook_form');
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
});

// Автосохранение при изменении полей
form.addEventListener('input', () => {
    saveFormData();
    errorDiv.style.display = 'none';
});

// Устанавливаем минимальную дату (сегодня)
const datetimeInput = form.datetime;
const now = new Date();
now.setMinutes(0, 0, 0);
const minDateTime = now.toISOString().slice(0, 16);
datetimeInput.min = minDateTime;

// Загружаем сохранённые данные
loadSavedData();

// Растягиваем приложение на весь экран Telegram
tg.expand();
