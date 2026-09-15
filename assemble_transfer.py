"""
Assemble MUSIC-ready transfer files from CLASS-aDM output.

CLASS is run in two gauges (see run_class.py). MUSIC's camb_file reader wants a
13-column CAMB-layout file that no single CLASS run produces, so we stitch:
  - densities  from the SYNCHRONOUS run, converted  T = -d / (k*h)^2   (class->CAMB)
  - velocities from the NEWTONIAN run,   converted  Tv = (1+z)/H(z) * (-t/(k*h)^2)
  - the ADM (idm_dr) rides in the "baryon slot"; do_adm in the .conf says what it is.

Produces three files (one per MUSIC run):
  {name}_baryon_transfer.dat      baryon slot = real baryons     (do_adm=0)
  {name}_adm_transfer.dat         baryon slot = ADM (idm_dr)     (do_adm=1)
  {name}_adm_baryon_transfer.dat  baryon slot = Omega-weighted baryon+ADM (do_adm=2)

Column layout the reader (transfer_camb.cc) consumes (13 cols, only 6 used):
  0:k  1:T_cdm  2:T_baryonSLOT  3,4,5:filler  6:T_tot  7,8,9:filler
  10:Tv_cdm  11:Tv_baryonSLOT  12:filler
"""
import numpy as np
from pathlib import Path
from config import load_config

CLASS_OUT    = Path("output/class")
TRANSFER_OUT = Path("output/transfer")

# --- column indices in CLASS format=class tk.dat (0-indexed) ---
# newtonian header: 1:k 2:d_g 3:d_b 4:d_cdm 5:d_idm_dr 6:d_ur 7:d_idr 8:d_tot
#                   9:phi 10:psi 11:t_g 12:t_b 13:t_cdm 14:t_idm_dr 15:t_ur 16:t_idr 17:t_tot
# synchronous is the same but WITHOUT t_cdm (defined to be zero), so it has one
# fewer column; the density indices below are unaffected (t_cdm is a high index).
COL = dict(k=0, d_b=2, d_cdm=3, d_idm=4, d_tot=7,   # densities (read from synchronous)
           t_b=11, t_cdm=12, t_idm=13)              # velocities (read from newtonian)


def _find_one(directory, pattern):
    """Find exactly one file matching a glob pattern; error if zero or many.
    Robust to CLASS's output index (e.g. '_00_') which varies by version."""
    matches = sorted(Path(directory).glob(pattern))
    if len(matches) == 0:
        raise FileNotFoundError(f"No file matching '{pattern}' in {directory}/ "
                                f"(did CLASS run and write here?)")
    if len(matches) > 1:
        raise ValueError(f"Expected one file for '{pattern}', found {len(matches)}: "
                         f"{[m.name for m in matches]}. Narrow the pattern.")
    return matches[0]


def _load_class_outputs(name, h):
    """Load the CLASS files this stage needs, checking each file has the
    columns we actually index into."""
    syn = np.loadtxt(_find_one(CLASS_OUT, f"{name}_synchronous_*tk.dat"))
    new = np.loadtxt(_find_one(CLASS_OUT, f"{name}_newtonian_*tk.dat"))
    bg  = np.loadtxt(_find_one(CLASS_OUT, f"{name}_newtonian_*background.dat"))

    # check each file has the columns we read from it (synchronous: densities up
    # to d_tot; newtonian: velocities up to t_idm). This tolerates the missing
    # t_cdm column in the synchronous file.
    if syn.shape[1] <= COL["d_tot"]:
        raise ValueError(
            f"synchronous tk has {syn.shape[1]} columns; need > {COL['d_tot']} "
            f"to read densities. COL indices may be wrong for this CLASS version.")
    if new.shape[1] <= COL["t_idm"]:
        raise ValueError(
            f"newtonian tk has {new.shape[1]} columns; need > {COL['t_idm']} "
            f"to read velocities. COL indices may be wrong for this CLASS version.")
    if syn.shape[0] != new.shape[0]:
        raise ValueError(
            f"synchronous ({syn.shape[0]} rows) and newtonian ({new.shape[0]} "
            f"rows) tk files are on different k-grids; cannot combine row-wise.")

    k = syn[:, COL["k"]]                        # h/Mpc (same grid in both)
    kh2 = (k * h) ** 2                          # (k in 1/Mpc)^2 for the convention factor
    return syn, new, bg, k, kh2

def _hubble_at_z(bg, z):
    """H(z) from the CLASS background file, interpolated. Column 0 is z,
    column 3 is H [1/Mpc] in CLASS's background output.
    NOTE: verify column 3 against your background file header once."""
    zc, Hc = bg[:, 0], bg[:, 3]
    order = np.argsort(zc)
    return float(np.interp(z, zc[order], Hc[order]))


def _to_camb_density(d, kh2):
    """class delta -> CAMB-convention transfer:  -d / (k*h)^2."""
    return -d / kh2


def _to_camb_velocity(t, kh2, z, Hz):
    """class theta -> velocity transfer in MUSIC's convention:
    (1+z)/H(z) * (t / (k*h)^2)."""
    return (1.0 + z) / Hz * (t / kh2)


def _write_transfer(path, k, T_cdm, T_bslot, T_tot, Tv_cdm, Tv_bslot):
    """Write the 13-column CAMB-layout file (fillers = 0)."""
    z = np.zeros_like(k)
    out = np.column_stack([k, T_cdm, T_bslot, z, z, z, T_tot,
                           z, z, z, Tv_cdm, Tv_bslot, z])
    header = ("k[h/Mpc]  T_cdm  T_baryonSLOT  g nu mnu  T_tot  no_nu tot_de Weyl "
              " Tv_cdm  Tv_baryonSLOT  vb-vc")
    np.savetxt(path, out, fmt="% .8e", header=header)
    print(f"   wrote {path.name}")


def assemble_transfer(cfg):
    name = cfg["run"]["name"]
    h = cfg["cosmology"]["h"]
    z = cfg["adm"]["z_start"]
    Omega_b = cfg["cosmology"]["Omega_b"]
    Omega_m = cfg["cosmology"]["Omega_m"]
    f_adm = cfg["adm"]["f_adm"]
    Omega_adm = f_adm * (Omega_m - Omega_b)      # Roy et al. convention: fraction of DM

    TRANSFER_OUT.mkdir(parents=True, exist_ok=True)
    syn, new, bg, k, kh2 = _load_class_outputs(name, h)
    Hz = _hubble_at_z(bg, z)
    print(f"[assemble] H(z={z}) = {Hz:.6e}  (sets velocity normalization)")

    # shared columns (same in every output file)
    T_cdm  = _to_camb_density(syn[:, COL["d_cdm"]], kh2)
    T_tot  = _to_camb_density(syn[:, COL["d_tot"]], kh2)
    Tv_cdm = _to_camb_velocity(new[:, COL["t_cdm"]], kh2, z, Hz)

    # per-species density (synchronous) / velocity (newtonian) for the baryon slot
    d_b, d_adm = syn[:, COL["d_b"]], syn[:, COL["d_idm"]]
    t_b, t_adm = new[:, COL["t_b"]], new[:, COL["t_idm"]]

    # 1) baryon run (do_adm=0): baryon slot = real baryons
    _write_transfer(TRANSFER_OUT / f"{name}_baryon_transfer.dat", k,
                    T_cdm, _to_camb_density(d_b, kh2), T_tot,
                    Tv_cdm, _to_camb_velocity(t_b, kh2, z, Hz))

    # 2) adm run (do_adm=1): baryon slot = ADM (idm_dr)
    _write_transfer(TRANSFER_OUT / f"{name}_adm_transfer.dat", k,
                    T_cdm, _to_camb_density(d_adm, kh2), T_tot,
                    Tv_cdm, _to_camb_velocity(t_adm, kh2, z, Hz))

    # 3) adm_baryon run (do_adm=2): baryon slot = Omega-weighted baryon+ADM
    w = Omega_b + Omega_adm
    d_comb = (Omega_b * d_b + Omega_adm * d_adm) / w
    t_comb = (Omega_b * t_b + Omega_adm * t_adm) / w
    _write_transfer(TRANSFER_OUT / f"{name}_adm_baryon_transfer.dat", k,
                    T_cdm, _to_camb_density(d_comb, kh2), T_tot,
                    Tv_cdm, _to_camb_velocity(t_comb, kh2, z, Hz))

    print("[assemble] wrote three transfer files to", TRANSFER_OUT)


if __name__ == "__main__":
    assemble_transfer(load_config())