const tg = window.Telegram.WebApp;
tg.ready();

document.getElementById('bookingForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const form = e.target;
    const data = {
        name: form.name.value,
        phone: form.phone.value,
        service: form.service.value,
        master: form.master.value,
        datetime: form.datetime.value
    };
    const dataString = JSON.stringify(data);
    tg.sendData(dataString);
    tg.close();
});
