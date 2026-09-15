"""
Generate the three MUSIC .conf files (baryon, aDM, aDM + baryon) from the config

The three runs share the halo backbone (box, seeds, region, shift) and differ only
in three things, which is what produces baryon.ics / adm.ics / adm_baryon.ics:
    run          transfer_file                do_adm  levelmax
    baryon       {name}_baryon_transfer.dat   0       levelmax
    adm          {name}_adm_transfer.dat      1       levelmax - 1   <- ADM one level coarser
    adm_baryon   {name}_adm_baryon_transfer   2       levelmax
"""

from pathlib import Path
from config import load_config

MUSIC_OUT    = Path("output/music")
TRANSFER_DIR = "output/transfer"


def _seed_lines(seeds, max_level):
    """Emit 'seed[L] = value' lines for levels <= max_level (so the coarser ADM
    run doesn't carry a seed above its levelmax)."""
    lines = []
    for level in sorted(seeds):
        if level <= max_level:
            lines.append(f"seed[{level}]\t= {seeds[level]}")
    return "\n".join(lines)


def _shift_str(shift):
    return ", ".join(str(s) for s in shift)


def write_music_conf(cfg, run, path):
    """Write one MUSIC .conf. run is 'baryon', 'adm', or 'adm_baryon'."""
    cos, adm, halo = cfg["cosmology"], cfg["adm"], cfg["halo"]
    name = cfg["run"]["name"]
 
    # per-run differences
    do_adm   = {"baryon": 0, "adm": 1, "adm_baryon": 2}[run]
    levelmax = halo["levelmax"] - 1 if run == "adm" else halo["levelmax"]
    transfer_file = f"{TRANSFER_DIR}/{name}_{run}_transfer.dat"
    ics_file = f"output/music/{name}_{run}.ics"
 
    # derived physics (same conventions as CLASS + the assembler)
    Omega_adm = adm["f_adm"] * (cos["Omega_m"] - cos["Omega_b"])   # fraction of DM
    DeltaN_adm = 4.4 * adm["xi"] ** 4
    Omega_L = 1.0 - cos["Omega_m"]
    H0 = 100.0 * cos["h"]
 
    text = f"""\
# MUSIC config, auto-generated. run: {name}_{run}  (do_adm={do_adm}, levelmax={levelmax})
 
[setup]
boxlength\t= {halo['box']}
zstart\t\t= {adm['z_start']}
levelmin\t= {halo['levelmin']}
levelmin_TF\t= {halo['levelmin']}
levelmax\t= {levelmax}
padding\t\t= 8
overlap\t\t= 4
align_top\t= no
use_2LPT\t= yes
baryons\t\t= yes
region\t\t= {halo['region_type']}
region_point_file\t= {halo['region_point_file']}
region_point_shift\t= {_shift_str(halo['region_point_shift'])}
region_point_levelmin\t= {halo['region_point_levelmin']}
 
[cosmology]
Omega_m\t\t= {cos['Omega_m']}
Omega_L\t\t= {Omega_L}
Omega_b\t\t= {cos['Omega_b']}
H0\t\t= {H0}
sigma_8\t\t= {cos['sigma_8']}
nspec\t\t= {cos['n_s']}
transfer\t= camb_file
transfer_file\t= {transfer_file}
### ADM params ###
do_adm\t\t= {do_adm}    # 0 (Baryons), 1 (ADM), 2 (Baryons+ADM)
Omega_adm\t= {Omega_adm:.6g}   # f_adm * (Omega_m - Omega_b)
DeltaN_adm\t= {DeltaN_adm:.6g}   # 4.4 * xi^4
 
[random]
cubesize\t= 256
{_seed_lines(halo['seeds'], levelmax)}
 
[output]
format\t\t= gadget2
gadget_lunit\t= kpc
gadget_coarsetype\t= 2
filename\t= {ics_file}
 
[poisson]
fft_fine\t= yes
accuracy\t= 1e-5
pre_smooth\t= 3
post_smooth\t= 3
smoother\t= gs
laplace_order\t= 6
grad_order\t= 6
"""
    with open(path, "w") as f:
        f.write(text)
    print(f"   wrote {path.name}  (do_adm={do_adm}, levelmax={levelmax}, "
          f"Omega_adm={Omega_adm:.5f})")
 
 
def generate_music_conf(cfg):
    MUSIC_OUT.mkdir(parents=True, exist_ok=True)
    name = cfg["run"]["name"]
    for run in ("baryon", "adm", "adm_baryon"):
        write_music_conf(cfg, run, MUSIC_OUT / f"{name}_{run}.conf")
    print("[music] wrote three configs to", MUSIC_OUT)
 
 
if __name__ == "__main__":
    generate_music_conf(load_config())