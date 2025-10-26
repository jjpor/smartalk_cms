
const TOKEN_STORAGE_KEY = "smartalk_auth_token";
const TOKEN_REFRESH_HEADER = "X-New-Auth-Token";

export function getAuthToken() {
    try { return sessionStorage.getItem(TOKEN_STORAGE_KEY); } catch { return null; }
}
export function setAuthToken(token) {
    try {
        if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
        else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch { }
}
export function clearAuthAndRedirect() {
    setAuthToken(null);
    window.location.href = "/dashboard.html";
}

export function showGlobalLoader() {
    const el = document.getElementById("globalLoader");
    if (!el) return;
    el.classList.add("active");
}
export function hideGlobalLoader() {
    const el = document.getElementById("globalLoader");
    if (!el) return;
    el.classList.remove("active");
}

export function showToast(msg, type = "ok", ms = 4000) {
    const t = document.getElementById("toast");
    if (!t) return;
    t.className = "";
    t.id = "toast";
    if (type === "error") t.classList.add("error");
    else if (type === "warn") t.classList.add("warn");
    t.textContent = msg;
    t.style.display = "block";
    setTimeout(() => { t.style.display = "none"; }, ms);
}

export async function apiGet(action, params = {}) {
    const token = getAuthToken();
    if (!token) { clearAuthAndRedirect(); return; }
    const url = new URL(`/api/coach/${action}`, window.location.origin);
    url.searchParams.set("_ts", Date.now());
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null) url.searchParams.set(k, v) });

    const res = await fetch(url.toString(), {
        headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.status === 401 || res.status === 403) { clearAuthAndRedirect(); return; }
    if (!res.ok) {
        let detail = await res.text().catch(() => res.statusText);
        throw new Error(detail || `GET ${action} failed`);
    }
    const newToken = res.headers.get(TOKEN_REFRESH_HEADER);
    if (newToken) setAuthToken(newToken);
    return res.json();
}

export async function apiPost(action, body = {}) {
    const isLogin = action === "login" || action === "loginWithGoogle";
    const url = isLogin ? "/api/auth/login" : `/api/coach/${action}`;
    const headers = { "Content-Type": "application/json" };

    const token = getAuthToken();
    if (!isLogin) {
        if (!token) { clearAuthAndRedirect(); return; }
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
    if (res.status === 401 || res.status === 403) { clearAuthAndRedirect(); return; }
    if (!res.ok) {
        let detail = await res.text().catch(() => res.statusText);
        throw new Error(detail || `POST ${action} failed`);
    }
    const newToken = res.headers.get(TOKEN_REFRESH_HEADER);
    if (newToken) setAuthToken(newToken);

    const json = await res.json().catch(() => ({}));
    if (isLogin && json?.success && json?.token) setAuthToken(json.token);
    return json;
}

export async function guardAuth() {
    const me = await apiGet("check_coach");
    return me
}


// listener per ogni bottone "pagina della dashboard" per aggiornare il token
container.querySelectorAll(".header-bar .header-nav a").forEach(link => {
    link.addEventListener('click', async e => {
        const rowNumber = e.target.dataset.row;
        showGlobalLoader();
        try {
            const single = await apiGet('getDebriefByRow', { rowNumber });
            if (single.success && single.draft) {
                fillDebriefFields(single.draft);

                // 💡 CORREZIONE CRITICA: SALVA IL NUMERO DI RIGA
                window.debriefLoadedRow = rowNumber;

                showToast("Draft loaded ✅", 3000, "bg-green-600");
            } else {
                showToast("Failed to load draft", 3000, "bg-red-600");
            }
        } catch (err) {
            showToast(`Error: ${err.message}`, 3000, "bg-red-600");
        } finally {
            hideGlobalLoader();
        }
    });
});