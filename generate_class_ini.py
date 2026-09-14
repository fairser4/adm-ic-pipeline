"""Generate adm-CLASS .ini files from the run config"""
from config import load_config
from pathlib import Path

OUTPUT_DIR = Path("output/class")

# --- Standard model reference values ---
ALPHA_SM = 0.00729735257                  # fine-structure constant
M_P = 0.9382720813                        # proton mass [GeV]
M_E   = 0.5109989461e-3                   # electron mass [GeV]

def derive_class_params(cfg):
  """Translate the config's inputs into CLASS conventions"""
  cos, adm = cfg["cosmology"], cfg["adm"]

  h2 = cos["h"]**2

  p = {}

  # --- computed: densities (note: omega = Omega * h^2; omega_cdm is TOTAL DM) ---
  p["omega_b"] = cos["Omega_b"] * h2
  p["omega_cdm"] = (cos["Omega_m"] - cos["Omega_b"]) * h2 # CLASS splits ADM out internally
  # --- computed: twin sector ---
  p["r_all_twin"] = adm["f_adm"]
  p["Delta_N_twin"] = 4.4 * adm["xi"] ** 4
  p["alphafs_dark"] = adm["alpha_dark_ratio"] * ALPHA_SM
  p["m_p_dark"]     = adm["m_p_ratio"] * M_P
  p["m_e_dark"]     = adm["m_e_ratio"] * M_E
  p["YHe_twin"]     = adm.get("YHe_twin", 0.0)
  # --- passed through ---
  p["h"]              = cos["h"]
  p["n_s"]            = cos["n_s"]
  p["sigma8"]         = cos["sigma_8"]
  p["z_pk"]           = adm["z_start"]
  p["P_k_max_h/Mpc"]  = cfg["class"]["P_k_max"]
  return p

def write_class_ini(cfg, gauge, path):
  """Write one CLASS .ini for the given gauge ('newtonian' or 'synchronous')."""
  p = derive_class_params(cfg)
  lines = [
    f"# run: {cfg['run']['name']}   gauge: {gauge}",
    "",
    "# --- cosmology ---",
    f"h = {p['h']}",
    f"omega_b = {p['omega_b']}",
    f"omega_cdm = {p['omega_cdm']}    # TOTAL dark matter; twin fraction split internally",
    f"n_s = {p['n_s']}",
    f"sigma8 = {p['sigma8']}",
    "k_pivot = 0.05",
    "",
    "# --- twin / ADM sector ---",
    f"r_all_twin = {p['r_all_twin']}      # f_adm = Omega_adm/Omega_dm",
    f"Delta_N_twin = {p['Delta_N_twin']}  # from xi' = T_dark/T_cmb",
    f"alphafs_dark = {p['alphafs_dark']}",
    f"m_p_dark = {p['m_p_dark']}          # GeV",
    f"m_e_dark = {p['m_e_dark']}          # GeV",
    f"YHe_twin = {p['YHe_twin']}",
    "Omega_idm_dr = 0    # zeroed: twin wrapper sets idm_dr internally",
    "N_idr = 0           # zeroed: twin wrapper sets dark radiation internally",
    "",
    "# --- output ---",
    f"z_pk = {p['z_pk']}",
    "output = dTk vTk mPk",
    f"gauge = {gauge}",
    f"P_k_max_h/Mpc = {p['P_k_max_h/Mpc']}",
    "write background = yes",
    "write thermodynamics = yes",
  ]
  with open(path, "w") as f:
    f.write("\n".join(lines) + "\n")
  print(f"wrote {path}")

if __name__ == "__main__":
  cfg = load_config()
  name = cfg["run"]["name"]
  OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  for gauge in ("newtonian", "synchronous"):
    path = OUTPUT_DIR / f"{name}_{gauge}.ini"
    write_class_ini(cfg, gauge, path)