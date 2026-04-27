const tg = window.Telegram.WebApp;
tg.ready();

const form = document.getElementById('bookingForm');
const submitBtn = document.getElementById('submitBtn');
const errorDiv = document.getElementById('formError');
const progressBar = document.getElementById('progressBar');
const progressFill = progressBar.querySelector('.progress-fill');
const totalPriceSpan = document.getElementById('totalPrice');
const serviceSelect = document.getElementById('serviceSelect');
let flatpickrInstance = null;

// Шаги формы
let currentStep = 1;
const steps = document.querySelectorAll('.step');

function showStep(step) {
    steps.forEach((s, idx) => {
        s.classList.toggle('active', idx === step-1);
    });
    currentStep = step;
}

document.querySelectorAll('.next-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (currentStep < steps.length) showStep(currentStep + 1);
    });
});
document.querySelectorAll('.prev-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (currentStep > 1) showStep(currentStep - 1);
    });
});
showStep(1);

function updatePrice() {
    const selected = serviceSelect.options[serviceSelect.selectedIndex];
    const price = selected.getAttribute('data-price') || 0;
    totalPriceSpan.textContent = 'Стоимость: ' + price + ' ₽';
}
serviceSelect.addEventListener('change', updatePrice);
updatePrice();

async function loadFreeSlots() {
    const master = document.querySelector('[name="master"]').value;
    const datetimeVal = document.getElementById('datetimePicker').value;
    if (!datetimeVal) return;
    const date = datetimeVal.split('T')[0];
    if (!master || !date) return;
    try {
        const response = await fetch(`/get_slots?master=${encodeURIComponent(master)}&date=${date}`);
        const data = await response.json();
        const busy = data.busy || [];
        const allSlots = [];
        for (let h = 9; h <= 20; h++) {
            for (let m = 0; m < 60; m += 30) {
                const slot = `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}`;
                if (!busy.includes(slot)) allSlots.push(slot);
            }
        }
        const slotInfo = document.getElementById('slotInfo');
        if (allSlots.length) {
            slotInfo.innerHTML = `<strong>🕒 Свободные слоты:</strong> ${allSlots.join(', ')}`;
        } else {
            slotInfo.innerHTML = `<strong>⚠️ Нет свободных слотов</strong> на эту дату. Выберите другую дату.`;
        }
    } catch (err) {
        console.error(err);
        document.getElementById('slotInfo').innerHTML = `<strong>❌ Ошибка загрузки слотов</strong>`;
    }
}

function initFlatpickr() {
    const datetimeInput = document.getElementById('datetimePicker');
    if (!datetimeInput) return;
    flatpickrInstance = flatpickr(datetimeInput, {
        enableTime: true,
        dateFormat: "Y-m-d\\TH:i",
        time_24hr: true,
        minuteIncrement: 30,
        minDate: "today",
        locale: "ru",
        onChange: async (selectedDates, dateStr) => {
            await loadFreeSlots();
            saveFormData();
        }
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
        if (data.master && data.datetime) loadFreeSlots();
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

    // Нормализуем дату (меняем пробел на T)
    let datetime = form.datetime.value;
    if (datetime.includes(' ')) datetime = datetime.replace(' ', 'T');

    const formData = {
        name: form.name.value.trim(),
        phone: form.phone.value.trim(),
        service: form.service.value,
        master: form.master.value,
        datetime: datetime
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

form.addEventListener('input', saveFormData);
document.querySelector('[name="master"]').addEventListener('change', () => {
    saveFormData();
    loadFreeSlots();
});

document.addEventListener('DOMContentLoaded', () => {
    initFlatpickr();
    loadSavedData();
    tg.expand();
});
