// Cliente da API (unica camada que fala com o backend).

async function req(method, url, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body != null) {
    if (isForm) opts.body = body;
    else { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = `Erro ${res.status}`;
    try { const j = await res.json(); detail = j.detail || detail; } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

export const api = {
  // meta
  formSchema: () => req("GET", "/api/form-schema"),

  // settings
  getSettings: () => req("GET", "/api/settings"),
  saveSettings: (data) => req("PUT", "/api/settings", data),
  uploadLogo: (file) => { const fd = new FormData(); fd.append("file", file); return req("POST", "/api/settings/logo", fd, true); },
  removeLogo: () => req("DELETE", "/api/settings/logo"),
  setPassword: (password) => req("POST", "/api/settings/password", { password }),
  verifyPassword: (password) => req("POST", "/api/settings/password/verify", { password }),
  saveRecovery: (data) => req("PUT", "/api/settings/recovery", data),
  resetRequest: (email) => req("POST", "/api/settings/password/reset-request", { email }),
  resetConfirm: (code, new_password) => req("POST", "/api/settings/password/reset-confirm", { code, new_password }),

  // patients
  listPatients: (search) => req("GET", "/api/patients" + (search ? `?search=${encodeURIComponent(search)}` : "")),
  getPatient: (id) => req("GET", `/api/patients/${id}`),
  createPatient: (data) => req("POST", "/api/patients", data),
  updatePatient: (id, data) => req("PUT", `/api/patients/${id}`, data),
  deletePatient: (id) => req("DELETE", `/api/patients/${id}`),

  // anamneses
  listAnamneses: (patientId) => req("GET", "/api/anamneses" + (patientId ? `?patient_id=${patientId}` : "")),
  getAnamnesis: (id) => req("GET", `/api/anamneses/${id}`),
  createAnamnesis: (patientId, data = {}) => req("POST", "/api/anamneses", { patient_id: patientId, data }),
  updateAnamnesis: (id, patch) => req("PATCH", `/api/anamneses/${id}`, patch),
  duplicateAnamnesis: (id) => req("POST", `/api/anamneses/${id}/duplicate`),
  deleteAnamnesis: (id) => req("DELETE", `/api/anamneses/${id}`),
  missing: (id) => req("GET", `/api/anamneses/${id}/missing`),
  pdfUrl: (id) => `/api/anamneses/${id}/pdf`,

  // appointments (agenda)
  listAppointments: (start, end) => req("GET", `/api/appointments?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
  upcoming: (limit = 8) => req("GET", `/api/appointments/upcoming?limit=${limit}`),
  getAppointment: (id) => req("GET", `/api/appointments/${id}`),
  createAppointment: (data) => req("POST", "/api/appointments", data),
  updateAppointment: (id, data) => req("PATCH", `/api/appointments/${id}`, data),
  deleteAppointment: (id) => req("DELETE", `/api/appointments/${id}`),

  // google agenda
  googleStatus: () => req("GET", "/api/google/status"),
  googleSaveConfig: (data) => req("PUT", "/api/google/config", data),
  googleConnect: () => req("POST", "/api/google/connect"),
  googleDisconnect: () => req("POST", "/api/google/disconnect"),

  // system
  info: () => req("GET", "/api/system/info"),
  backup: (destDir) => req("POST", "/api/system/backup", { dest_dir: destDir }),
  restore: (srcFile) => req("POST", "/api/system/restore", { src_file: srcFile }),
  exportTo: (path, format) => req("POST", "/api/system/export-to", { path, format }),
  savePdf: (anamnesisId, path) => req("POST", "/api/system/save-pdf", { anamnesis_id: anamnesisId, path }),
  importData: (file) => { const fd = new FormData(); fd.append("file", file); return req("POST", "/api/system/import", fd, true); },
};
