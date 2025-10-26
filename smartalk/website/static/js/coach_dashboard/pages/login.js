
import { apiPost, hideGlobalLoader, showGlobalLoader, showToast } from "/static/js/coach_dashboard/core/api_core.js";

const coachId = document.getElementById("coachId");
const password = document.getElementById("password");
const btn = document.getElementById("loginBtn");

btn?.addEventListener("click", async () => {
    try {
        showGlobalLoader();
        const resp = await apiPost("login", { coachId: coachId.value.trim(), password: password.value.trim() });
        if (!resp?.success) throw new Error(resp?.error || "Login failed");
        showToast("Welcome!", "ok");
        window.location.href = "/dashboard/coach/landing.html";
    } catch (e) {
        showToast(e.message || "Login error", "error");
    } finally {
        hideGlobalLoader();
    }
});
