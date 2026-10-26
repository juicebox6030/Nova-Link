"""Typical-only port coupling screen. NOT a worst-case safety qualification."""
from pathlib import Path
import json
p=Path(__file__).resolve().parent
out={'status':'TYPICAL_ONLY_NO_GUARANTEED_MARGIN','source':'Johanson antenna Rev3.1 p4; TI SWRS196I section8.1','subGHz_sampled_S21_dB':[-15.927,-14.992,-16.553],'twoG4_sampled_S21_dB':[-44.254,-43.149,-42.394],'MCU_advertised_ceiling_dBm_not_selected_operating_power':{'subGHz':14,'twoG4':5},'worst_case_coupling_bound':None,'IPC_attenuation_credited_dB':0}
out['sampled_subGHz_coupled_dBm']=14+max(out['subGHz_sampled_S21_dB'])
out['sampled_twoG4_coupled_dBm']=5+max(out['twoG4_sampled_S21_dB'])
out['difference_to_other_band_absmax_dB_not_guaranteed_margin']=[5-out['sampled_subGHz_coupled_dBm'],10-out['sampled_twoG4_coupled_dBm']]
out['reference_board_mm']=[50,30];out['candidate_board_mm']=[90,28];out['width_reduction_percent']=100*(30-28)/30
out['release_gates']=['Inactive powered/unpowered port impedance and stress','Full-band worst-case S parameters on actual PCB/enclosure','Match tuning and efficiency across fixtures','PCB stackup and land-pattern verification']
assert abs(out['sampled_subGHz_coupled_dBm']+.992)<1e-9
assert abs(out['sampled_twoG4_coupled_dBm']+37.394)<1e-9
(p/'antenna-screen.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
