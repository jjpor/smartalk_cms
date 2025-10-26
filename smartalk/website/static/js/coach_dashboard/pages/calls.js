
import { apiGet, apiPost, guardAuth, hideGlobalLoader, showGlobalLoader, showToast } from "/static/js/coach_dashboard/core/api_core.js";

const studentIdSelect = document.getElementById('studentId');
const productIdSelect = document.getElementById('productIdSelect');
const groupStudentsContainer = document.getElementById('groupStudentsContainer');
const groupStudentsDynamic = document.getElementById('groupStudentsDynamic');
const callDateInput = document.getElementById('callDate');
const hourlyRateInput = document.getElementById('hourlyRate');
const technicalDurationInput = document.getElementById('technicalDuration');
const callDurationSelect = document.getElementById('callDuration');
const unitsInput = document.getElementById('units');
const productIdInput = document.getElementById('productId');
const callMessageBox = document.getElementById('callMessageBox');
const remainingCallsDisplay = document.getElementById('remainingCalls');
const attendanceRowInd = document.getElementById('attendanceRowInd');
const notesGeneral = document.getElementById('notes');

// Modal
const modal = document.getElementById("studentDetailsModal");
const modalAttendance = document.getElementById("modalAttendance");
const modalNotes = document.getElementById("modalNotes");
const modalStudentId = document.getElementById("modalStudentId");
const modalCancelBtn = document.getElementById("modalCancelBtn");
const modalSaveBtn = document.getElementById("modalSaveBtn");

let CURRENT_COACH_NAME = "";
let perStudentDetails = new Map();
let CURRENT_GROUP_STUDENTS = [];

function openModal(studentId) {
    modal.classList.add("open");
    modalStudentId.value = studentId || "";
    modalAttendance.value = perStudentDetails.get(studentId)?.attendance || "";
    modalNotes.value = perStudentDetails.get(studentId)?.notes || "";
}
function closeModal() { modal.classList.remove("open"); }
modalCancelBtn.addEventListener("click", closeModal);
modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
modalSaveBtn.addEventListener("click", () => {
    const sid = modalStudentId.value;
    const att = modalAttendance.value;
    const nts = modalNotes.value;
    if (!att) { showToast("Attendance is required", "warn"); return; }
    perStudentDetails.set(sid, { attendance: att, notes: nts });
    showToast(`Saved details for ${sid}`, "ok", 2000);
    closeModal();
});

function setMsg(msg, ok = true) {
    callMessageBox.textContent = msg || "";
    callMessageBox.style.color = ok ? "#065f46" : "#b91c1c";
}

function recomputeUnitsAndRate() {
    const override = parseFloat(callDurationSelect.value || '0');
    const native = parseFloat(technicalDurationInput.value || '0');
    const units = (!native || !override) ? 0 : (override / native);
    unitsInput.value = units ? units.toFixed(2) : '';

    const baseRateTotal = parseFloat(hourlyRateInput.dataset.baseRate || '0');
    const attendees = parseInt(hourlyRateInput.dataset.attendees || '1', 10) || 1;
    const callType = document.querySelector('input[name="callType"]:checked').value;

    const perStudentBase = attendees > 0 ? (baseRateTotal / attendees) : baseRateTotal;
    const ratePerStudent = perStudentBase * units;
    const rateTotal = ratePerStudent * attendees;

    if (callType === "IND") hourlyRateInput.value = ratePerStudent > 0 ? ratePerStudent.toFixed(2) : '';
    else hourlyRateInput.value = rateTotal > 0 ? rateTotal.toFixed(2) : '';
}

(async () => {
    const me = await guardAuth();
    showGlobalLoader();
    callDateInput.value = new Date().toISOString().slice(0, 10);
    await loadStudentIds();
    hideGlobalLoader();
})();

async function loadStudentIds() {
    studentIdSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';
    productIdSelect.innerHTML = '<option value="" disabled selected>Select a student first</option>';
    productIdSelect.disabled = true;
    try {
        const resp = await apiGet("getStudents");
        const arr = resp?.students || [];
        arr.sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));
        studentIdSelect.innerHTML = '<option value="" disabled selected>Select a student</option>';
        arr.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id; opt.textContent = id; studentIdSelect.appendChild(opt);
        });
    } catch (e) {
        studentIdSelect.innerHTML = '<option value="" disabled selected>Error loading</option>';
    }
}

async function loadGroupProducts() {
    productIdSelect.disabled = true;
    productIdSelect.innerHTML = '<option value="" disabled selected>Loading group products...</option>';
    try {
        const resp = await apiGet("getGroupProducts");
        const prods = resp?.products || [];
        productIdSelect.innerHTML = '<option value="" disabled selected>Select a group product</option>';
        prods.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.productId;
            opt.textContent = `${p.productName}`;
            opt.dataset.product = JSON.stringify(p);
            productIdSelect.appendChild(opt);
        });
        productIdSelect.disabled = false;
    } catch (e) {
        productIdSelect.innerHTML = '<option value="" disabled selected>Error loading group products</option>';
    }
}

productIdSelect.addEventListener("change", async () => {
    const callType = document.querySelector('input[name="callType"]:checked').value;
    const opt = productIdSelect.options[productIdSelect.selectedIndex];
    const selectedProductId = productIdSelect.value;
    productIdInput.value = selectedProductId || '';

    hourlyRateInput.value = ''; technicalDurationInput.value = '';
    remainingCallsDisplay.style.display = "none";

    let prod = {};
    try { prod = JSON.parse(opt?.dataset?.product || "{}"); } catch { }
    const nativeDuration = prod.duration || "";
    technicalDurationInput.value = nativeDuration;
    hourlyRateInput.dataset.baseRate = String(prod.rate);
    hourlyRateInput.dataset.attendees = String(prod.participants);

    if (nativeDuration) {
        let exists = [...callDurationSelect.options].some(o => o.value == nativeDuration);
        if (!exists) {
            const newOpt = document.createElement('option'); newOpt.value = nativeDuration; newOpt.textContent = nativeDuration;
            callDurationSelect.appendChild(newOpt);
        }
        callDurationSelect.value = nativeDuration;
    }

    if (callType === "IND") {
        const remaining = opt?.dataset?.remainingCalls;
        if (remaining !== undefined && remaining !== "" && remaining !== "null" && remaining !== "undefined") {
            remainingCallsDisplay.textContent = `Remaining: ${remaining} calls`;
            remainingCallsDisplay.style.display = "block";
        }
    } else {
        try {
            const resp = await apiGet("getGroupStudents", { productId: selectedProductId });
            const studs = resp?.students || [];
            CURRENT_GROUP_STUDENTS = studs;
            renderGroupStudents(prod.participants || studs.length || 2, studs);
        } catch (e) {
            renderGroupStudents(2, []);
        }
    }

    recomputeUnitsAndRate();
});

function renderGroupStudents(n, studs) {
    groupStudentsDynamic.innerHTML = "";
    perStudentDetails = new Map();
    for (let i = 0; i < n; i++) {
        const row = document.createElement("div");
        row.style.display = "grid";
        row.style.gridTemplateColumns = "1fr auto";
        row.style.gap = "8px";
        row.style.marginBottom = "8px";

        const sel = document.createElement("select");
        sel.className = "form-input";
        sel.innerHTML = `<option value="" disabled selected>Select student ${i + 1}</option>`;
        studs.forEach(sid => {
            const o = document.createElement("option");
            o.value = sid; o.textContent = sid; sel.appendChild(o);
        });

        const btn = document.createElement("button");
        btn.type = "button"; btn.className = "btn secondary"; btn.textContent = "Details";
        btn.addEventListener("click", () => {
            if (!sel.value) { showToast("Select the student first", "warn"); return; }
            openModal(sel.value);
        });

        sel.addEventListener("change", () => {
            if (sel.value && !perStudentDetails.has(sel.value)) {
                perStudentDetails.set(sel.value, { attendance: "", notes: "" });
            }
        });

        row.appendChild(sel);
        row.appendChild(btn);
        groupStudentsDynamic.appendChild(row);
    }
}

document.querySelectorAll('input[name="callType"]').forEach(r => {
    r.addEventListener("change", async () => {
        const isGroup = r.value === "GROUP" && r.checked;
        attendanceRowInd.style.display = isGroup ? "none" : "block";
        studentIdSelect.closest("div").style.display = isGroup ? "none" : "block";
        groupStudentsContainer.style.display = isGroup ? "block" : "none";

        productIdSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';
        productIdSelect.disabled = true;
        hourlyRateInput.value = ''; technicalDurationInput.value = ''; productIdInput.value = '';
        callDurationSelect.value = ''; unitsInput.value = '';

        if (isGroup) await loadGroupProducts();
        else await loadStudentIds();
    });
});

callDurationSelect.addEventListener("change", recomputeUnitsAndRate);

document.getElementById("callForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
        showGlobalLoader();
        const callType = document.querySelector('input[name="callType"]:checked').value;
        const payload = {
            callDate: callDateInput.value,
            callDuration: parseFloat(callDurationSelect.value),
            units: parseFloat(unitsInput.value),
            hourlyRate: parseFloat(hourlyRateInput.value) || 0,
            coachName: CURRENT_COACH_NAME,
            productId: productIdInput.value || productIdSelect.value || '',
            notes: notesGeneral.value || ""
        };

        if (callType === "IND") {
            payload.studentId = studentIdSelect.value;
            payload.attendance = (document.getElementById("attendance").value || "YES");
        } else {
            const selects = groupStudentsDynamic.querySelectorAll("select");
            const ids = Array.from(selects).map(s => s.value).filter(Boolean);
            if (!ids.length) throw new Error("Select all group students");
            const perStudent = ids.map(sid => {
                const det = perStudentDetails.get(sid);
                if (!det || !det.attendance) throw new Error(`Missing attendance for ${sid}`);
                return { studentId: sid, attendance: det.attendance, notes: det.notes || "" };
            });
            payload.isGroup = true;
            payload.perStudent = perStudent;
        }

        const resp = await apiPost("logCall", payload);
        if (!resp?.success) throw new Error(resp?.error || "Error logging call");
        showToast("Call logged successfully");
        setMsg("Call logged successfully", true);
        document.getElementById("callForm").reset();
        callDateInput.value = new Date().toISOString().slice(0, 10);
    } catch (e) {
        setMsg(e.message || "Submit error", false);
    } finally {
        hideGlobalLoader();
    }
});
