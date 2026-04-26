const tg = window.Telegram.WebApp;
tg.ready();

// Элементы
const form = document.getElementById('bookingForm');
const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const errorDiv = document.getElementById('formError');
const successDiv = document.getElementById('formSuccess');
const progressBar = document.getElementById('progressBar');
const progressFill = progressBar.querySelector('.progress-fill');
const totalPriceSpan = document.getElementById('totalPrice');
const serviceSelect = document.getElementById('serviceSelect');

// Цены услуг (можно вынести в data-атрибуты)
const prices = {
    "💅 Маникюр": 1500,
    "🦶 Педикюр": 2500,
    "💆‍♀️ Спа-уход": 3500
};

// Обновление итоговой цены
function updatePrice() {
    const selectedOption = serviceSelect.options[serviceSelect.selectedIndex];
    const price = parseInt(selectedOption.getAttribute('data-price')) || 0;
    totalPriceSpan.textContent = price + ' ₽';
}
serviceSelect.addEventListener('change', updatePrice);
updatePrice();

// Инициализация календаря Flatpickr (с временем)
let flatpickrInstance;
function initCalendar() {
    flatpickrInstance = flatpickr("#datetimePicker", {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        minuteIncrement: 30,
        minDate: "today",
        locale: "ru",
        disable: [
            function(date) {
                // Запрещаем воскресенье (0) и субботу (6) – пример
                // return date.getDay() === 0 || date.getDay() === 6;
                return false; // пока без ограничений
            }
        ],
        onChange: function(selectedDates, dateStr, instance) {
            // Можно дополнительно проверить занятые слоты через API бота
            // console.log(dateStr);
        }
    });
}
initCalendar();

// Автосохранение в localStorage
function loadSavedData() {
    const saved = localStorage.getItem('beautybook_form');
    if (saved) {
        const data = JSON.parse(saved);
        for (const [key, value] of Object.entries(data)) {
            const input = form.elements[key];
            if (input) input.value = value;
        }
        if (data.datetime) flatpickrInstance.setDate(data.datetime, false);
        updatePrice();
    }
}
function saveFormData() {
    const data = {};
    for (let i = 0; i < form.elements.length; i++) {
        const el = form.elements[i];
        if (el.name) data[el.name] = el.value;
    }
    localStorage.setItem('beautybook_form', JSON.stringify(data));
}
form.addEventListener('input', () => saveFormData());

// Валидация
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

// Отправка формы с анимацией прогресса
async function submitForm(e) {
    e.preventDefault();
    const errorMsg = validateForm();
    if (errorMsg) {
        errorDiv.textContent = errorMsg;
        errorDiv.style.display = 'block';
        return;
    }
    errorDiv.style.display = 'none';
    // Показать прогресс-бар и заблокировать кнопку
    progressBar.style.display = 'block';
    progressFill.style.width = '0%';
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Отправка...';

    // Анимация прогресса до 90%
    let width = 0;
    const interval = setInterval(() => {
        if (width >= 90) clearInterval(interval);
        else {
            width += 10;
            progressFill.style.width = width + '%';
        }
    }, 100);

    // Собираем данные
    const formData = {
        name: form.name.value.trim(),
        phone: form.phone.value.trim(),
        service: form.service.value,
        master: form.master.value,
        datetime: form.datetime.value
    };
    try {
        tg.sendData(JSON.stringify(formData));
        // Достигаем 100%
        clearInterval(interval);
        progressFill.style.width = '100%';
        successDiv.style.display = 'block';
        successDiv.textContent = '✅ Заявка отправлена! Приложение закроется...';
        setTimeout(() => {
            tg.close();
        }, 1500);
    } catch (err) {
        console.error(err);
        clearInterval(interval);
        progressBar.style.display = 'none';
        errorDiv.textContent = 'Ошибка отправки. Попробуйте позже.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = '✅ Записаться';
    }
}
form.addEventListener('submit', submitForm);

// Сброс формы
resetBtn.addEventListener('click', () => {
    form.reset();
    localStorage.removeItem('beautybook_form');
    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';
    progressBar.style.display = 'none';
    flatpickrInstance.clear();
    updatePrice();
});

// Загружаем сохранённые данные
loadSavedData();

// Растягиваем приложение
tg.expand();
