const socket = io("http://localhost:5000");

const speedEl = document.getElementById("speed");
const rpmEl = document.getElementById("rpm");

let state = {
    speed: 0,
    rpm: 0
};

socket.on("connect", () => {
    console.log("Connected");
});

socket.on("analytics", (data) => {

    if (typeof data === "string")
        data = JSON.parse(data);

    if (data.speed !== undefined)
        state.speed = Math.round(data.speed);

    if (data.rpm !== undefined)
        state.rpm = Math.round(data.rpm);
});

setInterval(() => {

    speedEl.textContent = state.speed;
    rpmEl.textContent = state.rpm;

}, 50); // 20 FPS