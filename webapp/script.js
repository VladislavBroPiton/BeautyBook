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
let refreshInterval = null;

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

// Загрузка свободных слотов
async function loadFreeSlots() {
    console.log('📡 loadFreeSlots вызвана');
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
            slotInfo.innerHTML = `<strong>⚠️ Нет свободных слотов</strong> на эту дату.`;
        }
    } catch (err) {
        console.error(err);
        document.getElementById('slotInfo').innerHTML = `<strong>❌ Ошибка загрузки слотов</strong>`;
    }
}

function startAutoRefresh() {
    console.log('🔄 startAutoRefresh');
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
        console.log('⏰ Автообновление слотов...');
        const picker = document.getElementById('datetimePicker');
        if (picker && picker.value) loadFreeSlots();
    }, 5000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Flatpickr
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
            console.log('📅 Выбрана дата/время:', dateStr);
            await loadFreeSlots();
            startAutoRefresh();
            saveFormData();
        }
    });
}

// Сохранение и восстановление
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
        if (data.master && data.datetime) {
            loadFreeSlots();
            startAutoRefresh();
        }
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
    if (selected < new Date()) return "Дата не может быть в прошлом";
    return null;
}

// Отправка формы (клиент)
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
    } finally {
        stopAutoRefresh();
    }
});

form.addEventListener('input', saveFormData);
document.querySelector('[name="master"]').addEventListener('change', () => {
    saveFormData();
    loadFreeSlots();
    startAutoRefresh();
});

window.addEventListener('beforeunload', stopAutoRefresh);

// ---------- НОВОЕ: МАСТЕР-РЕЖИМ ----------
const masterSection = document.getElementById('masterSection');
const showMasterBtn = document.getElementById('showMasterBtn');
const masterLogin = document.getElementById('masterLogin');
const masterContent = document.getElementById('masterContent');
const masterPassword = document.getElementById('masterPassword');
const masterLoginBtn = document.getElementById('masterLoginBtn');
const masterAppointmentsDiv = document.getElementById('masterAppointments');
const masterLogoutBtn = document.getElementById('masterLogoutBtn');

let masterActive = false;

showMasterBtn.addEventListener('click', () => {
    if (!masterActive) {
        form.style.display = 'none';
        masterSection.style.display = 'block';
        masterLogin.style.display = 'block';
        masterContent.style.display = 'none';
        masterPassword.value = '';
        masterActive = true;
    } else {
        masterSection.style.display = 'none';
        form.style.display = 'block';
        masterActive = false;
    }
});

masterLoginBtn.addEventListener('click', async () => {
    const password = masterPassword.value.trim();
    if (!password) return;

    // Безопасно получаем ID пользователя из Telegram WebApp API
    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) {
        alert('Ошибка: не удалось определить пользователя Telegram');
        return;
    }

    try {
        const resp = await fetch('/master_api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'login',
                password,
                user_id: userId       // ← отправляем ID напрямую
            })
        });
        const data = await resp.json();
        if (data.success) {
            masterLogin.style.display = 'none';
            masterContent.style.display = 'block';
            loadMasterAppointments(password, userId);
        } else {
            alert(data.error || 'Ошибка входа');
        }
    } catch (e) {
        alert('Сетевая ошибка');
    }
});

async function loadMasterAppointments(password, userId) {
    try {
        const resp = await fetch('/master_api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'list',
                password,
                user_id: userId
            })
        });
        const data = await resp.json();
        if (data.success) {
            renderMasterAppointments(data.appointments || []);
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert('Ошибка загрузки');
    }
}

function renderMasterAppointments(appointments) {
    if (!appointments.length) {
        masterAppointmentsDiv.innerHTML = '<p>Нет активных записей</p>';
        return;
    }
    let html = '';
    appointments.forEach(app => {
        html += `
        <div class="appointment-card">
            <div><strong>${app.date} ${app.time}</strong> - ${app.service}</div>
            <div>Клиент: ${app.client_name} | ${app.client_phone}</div>
            <div>Цена: ${app.price} руб.</div>
            <button class="cancel-appointment-btn" data-id="${app.id}">Отменить</button>
        </div>`;
    });
    masterAppointmentsDiv.innerHTML = html;
    document.querySelectorAll('.cancel-appointment-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const id = e.target.getAttribute('data-id');
            if (confirm('Отменить запись?')) {
                const userId = tg.initDataUnsafe?.user?.id;
                const password = masterPassword.value.trim();
                const resp = await fetch('/master_api', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        action: 'cancel',
                        appointment_id: id,
                        password,
                        user_id: userId
        })
    });
    const data = await resp.json();
    if (data.success) {
        loadMasterAppointments(password, userId);
    } else {
        alert(data.error || 'Не удалось отменить');
    }
}
        });
    });
}

masterLogoutBtn.addEventListener('click', () => {
    masterContent.style.display = 'none';
    masterLogin.style.display = 'block';
    masterPassword.value = '';
});

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    initFlatpickr();
    loadSavedData();
    tg.expand();
});
