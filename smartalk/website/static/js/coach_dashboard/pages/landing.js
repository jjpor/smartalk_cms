
import { guardAuth } from "/static/js/coach_dashboard/core/api_core.js";

(async () => {
    const me = await guardAuth();
    if (me?.name) document.getElementById("coachName").textContent = me.name;
})();
