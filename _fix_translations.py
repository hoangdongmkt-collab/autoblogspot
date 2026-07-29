import json
from pathlib import Path

new_keys = {
    "vi": {
        "sett_tab_account":  "Tài khoản",
        "sett_pwd_change":   "Đổi mật khẩu",
        "sett_pwd_current":  "Mật khẩu hiện tại",
        "sett_pwd_new":      "Mật khẩu mới",
        "sett_pwd_confirm":  "Xác nhận mật khẩu mới",
        "sett_pwd_hint":     "Ít nhất 6 ký tự",
        "sett_pwd_save":     "Lưu mật khẩu mới",
        "sett_pwd_fill_all": "Vui lòng điền đầy đủ tất cả các trường",
        "sett_saving":       "Đang lưu",
    },
    "en": {
        "sett_tab_account":  "Account",
        "sett_pwd_change":   "Change Password",
        "sett_pwd_current":  "Current Password",
        "sett_pwd_new":      "New Password",
        "sett_pwd_confirm":  "Confirm New Password",
        "sett_pwd_hint":     "At least 6 characters",
        "sett_pwd_save":     "Save New Password",
        "sett_pwd_fill_all": "Please fill in all fields",
        "sett_saving":       "Saving",
    },
    "fr": {
        "sett_tab_account":  "Compte",
        "sett_pwd_change":   "Changer le mot de passe",
        "sett_pwd_current":  "Mot de passe actuel",
        "sett_pwd_new":      "Nouveau mot de passe",
        "sett_pwd_confirm":  "Confirmer le nouveau mot de passe",
        "sett_pwd_hint":     "Au moins 6 caractères",
        "sett_pwd_save":     "Enregistrer le nouveau mot de passe",
        "sett_pwd_fill_all": "Veuillez remplir tous les champs",
        "sett_saving":       "Enregistrement",
    },
    "it": {
        "sett_tab_account":  "Account",
        "sett_pwd_change":   "Cambia password",
        "sett_pwd_current":  "Password attuale",
        "sett_pwd_new":      "Nuova password",
        "sett_pwd_confirm":  "Conferma nuova password",
        "sett_pwd_hint":     "Almeno 6 caratteri",
        "sett_pwd_save":     "Salva nuova password",
        "sett_pwd_fill_all": "Si prega di compilare tutti i campi",
        "sett_saving":       "Salvataggio",
    },
}

for lang, keys in new_keys.items():
    p = Path(f"translations/{lang}.json")
    data = json.loads(p.read_bytes().decode("utf-8-sig"))
    data.update(keys)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"OK {lang}.json — {len(data)} keys")
