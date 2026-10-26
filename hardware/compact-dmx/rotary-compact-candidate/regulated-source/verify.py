"""Independent primary-based literal pin/passive/state/DC checks; no generator import."""
from pathlib import Path
from itertools import product
import xml.etree.ElementTree as E,json,math,hashlib,re
P=Path(__file__).resolve().parent;root=P.parents[3];r=E.parse(P/'regulated-source.net');comps={c.attrib['ref']:c for c in r.findall('./components/comp')};pins={x.attrib['ref']+'.'+x.attrib['pin']:n.attrib['name'].rsplit('/',1)[-1] for n in r.findall('./nets/net') for x in n}
g='GND_ISO';v='REG_5V136';raw='FPC_5V';vi='PROTECTED_IN';o='USB_VBUS'
expected={
'U1':{1:'INPUT_UVLO',2:'INPUT_OVLO',3:None,4:g,5:raw,6:vi,7:'INPUT_DVDT',8:g,9:'INPUT_ILM',10:None},
'U2':{1:g,2:'REG_READY_OD',3:'REG_VAUX',4:g,5:'REG_FB',6:None,7:v,8:v,9:'SW_L2',10:g,11:'SW_L1',12:vi,13:vi,14:vi,15:g},
'U3':{1:'PORT_FAULT_OD',2:v,3:v,4:v,5:v,6:'REG_READY_OD',7:v,8:g,9:'REF_RTN',10:'REF',11:'USB_CC1',12:g,13:'USB_CC2',14:o,15:o,16:None,17:None,18:None,19:None,20:None,21:g},
'J1':{'A1_B12':g,'A4_B9':o,'B8':None,'A5':'USB_CC1','B7':'USB_D_SHORT','A6':'USB_D_SHORT','A7':'USB_D_SHORT','B6':'USB_D_SHORT','A8':None,'B5':'USB_CC2','B4_A9':o,'B1_A12':g,'S1':g,'S2':g,'S3':g,'S4':g}}
for ref,pp in expected.items():
 for num,net in pp.items():
  actual=pins.get(ref+'.'+str(num),'');assert actual==net if net is not None else actual.startswith('unconnected-'),(ref,num,actual,net)
for ref,mpn in [('U1','TPS259474LRPWR'),('U2','TPS63070RNMR'),('U3','TPS25810RVCR'),('J1','USB4105-GF-A')]:assert comps[ref].findtext('value')==mpn
res={'R1':(24900,raw,'INPUT_UVLO'),'R2':(10000,'INPUT_UVLO',g),'R3':(37400,raw,'INPUT_OVLO'),'R4':(10000,'INPUT_OVLO',g),'R5':(1000,'INPUT_ILM',g),'R6':(54200,v,'REG_FB'),'R7':(10000,'REG_FB',g),'R8':(100000,v,'REG_READY_OD'),'R9':(100000,'REG_READY_OD',g),'R10':(100000,'REF','REF_RTN'),'R11':(100000,v,'PORT_FAULT_OD')}
for ref,(ohm,a,b) in res.items():
 # Vishay28758 TNPW0402 0.1%/10ppm supported range47ohm..100kohm.
 assert 47<=ohm<=100000,(ref,'unsupported exact precision ordering range',ohm)
 assert (pins[ref+'.1'],pins[ref+'.2'])==(a,b);value=comps[ref].findtext('value');assert str(ohm)+'ohm' in value and 'BYED' in value
caps={'C1':(10e-6,vi),'C2':(10e-6,vi),'C3':(10e-6,vi),'C4':(22e-6,v),'C5':(22e-6,v),'C6':(22e-6,v),'C7':(10e-6,v),'C8':(150e-6,v),'C9':(10e-6,o),'C10':(.1e-6,v),'C11':(.1e-6,'REG_VAUX'),'C12':(.01e-6,'INPUT_DVDT'),'C13':(.1e-6,raw)}
for ref,(cv,a) in caps.items():
 assert (pins[ref+'.1'],pins[ref+'.2'])==(a,g);val=float(re.search(r' (\d+(?:\.\d+)?)((?:u|n)F)',comps[ref].findtext('value'))[1]);mult=1e-6 if 'uF' in comps[ref].findtext('value') else 1e-9;assert abs(cv-val*mult)<1e-12
assert (pins['L1.1'],pins['L1.2'])==('SW_L1','SW_L2')
assert (pins['D1.1'],pins['D1.2'])==(o,g)
assert pins['J0.1']==raw and pins['J0.2']==g and pins['TP1.1']=='PORT_FAULT_OD'
assert {key for key,net in pins.items() if net=='REG_VAUX'}=={'U2.3','C11.1'}
assert pins['U2.1']==g # forcePWM, not typicalPFM+3% substituted
assert pins['U3.9']!=g and pins['R10.2']==pins['U3.9']
# Corners: initial.1% +100K*10ppm =.2%; aging not included.
tol=.002
def divider(top,bottom,refs,bias):return [ref*(1+top*(1+a)/(bottom*(1+b)))+i*top*(1+a) for a,b,ref,i in product([-tol,tol],[-tol,tol],refs,[-bias,bias])]
regs=divider(54200,10000,[.792,.808],100e-9);lo,hi=min(regs),max(regs);assert abs(.8*(1+54200/10000)-5.136)<1e-12
uv=divider(24900,10000,[1.183,1.223],.1e-6);uvfall=divider(24900,10000,[1.076,1.116],.1e-6);ov=divider(37400,10000,[1.183,1.223],.1e-6)
assert min(ov)>5.3625 and max(uv)<4.6375
breaker=[3334/(1000*(1+t))*(1+a) for t,a in product([-tol,tol],[-.1,.1])]
boardR=.020 # total regulator/controller/receptacle copper/solder allocation; not FPC terminations
connector_loop_alloc=.025 # complete mated50mohm/contact loop,4VBUS+4GND equalsharing; not split into undocumented internal losses
portlo=lo-1.5*(.055+boardR+connector_loop_alloc);porthi=hi
# Unproven engineering allocation for typ-only line/load plus ripple/transient.
static_extra=.005*5.136;dynamic_allowance=.100
screenlo=portlo-static_extra-dynamic_allowance;screenhi=porthi+static_extra+dynamic_allowance
assert screenlo>4.75 and screenhi<5.5
# Source power: solve hot/process FPC loop+efuse at converter input power.
length=1.046167656;rho=1.75e-8;alpha=.00393
flexR=2*length*rho/(.0078*70e-6*.9)*(1+alpha*(80-20));termR=.020;efuseR=.045;R=flexR+termR+efuseR
source_min=5*(1-.025)-5*.0003*25-.200 # full200mVpp reserved one-sided, not +/-100mV
source_max=5*(1+.025)+5*.0003*25+.200
cases=[]
for eta,vconn in product([.8,.85,.9],[0,.2,.410]):
 ireg=1.5+vconn+.001;preg=hi*ireg;power=preg/eta+.005
 disc=source_min**2-4*R*power;assert disc>0
 current=(source_min-math.sqrt(disc))/(2*R);vin=source_min-current*R
 # TI boostIpeak with effectiveL1.05uH, minfs2.1MHz; model not an all-corner max.
 D=max(0,(hi-vin)/hi);ripple=vin*D/(2.1e6*1.05e-6);peak=current+ripple/2
 assert vin>3 and current<min(breaker) and ireg<2
 cases.append({'eta_allocation':eta,'VCONN_A':vconn,'reg_output_A':ireg,'reg_output_W':preg,'FPC_input_A':current,'reg_input_V':vin,'module_DC_current_margin_to4A':4-current,'breaker_min_margin_A':min(breaker)-current,'inductor_peak_model_A':peak,'RHP_zero_Hz_at1p8uH':((1-D)**2*hi)/(2*math.pi*ireg*1.8e-6),'TI3p05A_testpoint_margin_to_average_A':3.05-current,'flex_copper_loss_W':current*current*flexR,'termination_loss_W':current*current*termR,'input_eFuse_loss_W':current*current*efuseR,'regulator_loss_alloc_W':preg*(1/eta-1),'module_output_W':source_min*current})
worst=max(cases,key=lambda x:x['FPC_input_A'])
# Cross-check quadratic independently by fixed point for worst corner.
i=2
for _ in range(80):i=(worst['reg_output_W']/.8+.005)/(source_min-i*R)
assert abs(i-worst['FPC_input_A'])<1e-10
assert worst['inductor_peak_model_A']*1.2<4.1 # Coilcraft25C saturation test point only
# Startup controller EN low while PG low, released to enable atPG high.
en_low=.4;en_high=lo*99800/(100200+99800)-.7e-6/(1/100200+1/99800)
# TPS25810 recommended operating logic limits, rather than switching thresholds.
assert en_low<.63 and en_high>1.17
# Manufacturer attachment truth table, both orientations. No USB protocol simulator.
ccrows=[('open','open',False,None),('Rd','open',True,None),('open','Rd',True,None),('Rd','Ra',True,'CC2'),('Ra','Rd',True,'CC1'),('open','Ra',False,None),('Ra','open',False,None),('Rd','Rd',False,None),('Ra','Ra',False,None)]
states=[]
for ready,(cc1,cc2,attach,vc) in product([False,True],ccrows):
 states.append({'REG_PG':ready,'CC1':cc1,'CC2':cc2,'VBUS_enabled':ready and attach,'VCONN_on':vc if ready and attach else None,'advertisement_A':1.5 if ready else None})
assert len(states)==18
# Port discharge conditional RC10uF+20%tol+15% allocation at600ohm.
discharge=12e-6*1.15*600*math.log(hi/.8);assert discharge<.039
faults=[
 {'fault':'USB VBUS short','behavior':'TPS25810 currentlimit1.58..1.82A, response4us max only specifiedtest; thermalcycling. Full VBUS1.82+VCONN0.410+.001=2.231A exceeds converter2A recommendedmax; continuedoperation not required. Current/faultduration/thermal benchgate.'},
 {'fault':'VCONN short','behavior':'TPS25810 separate300..410mA limit and3us max response atspecifiedtest. Budget includes410mA as stresscase, not promised healthy cableload.'},
 {'fault':'Regulator input short','behavior':'U1 circuitbreaker/latchoff,3.334A nominal+/-10%; currentmayexceed before fasttrip; no guaranteedflexI2t/thermal proof.'},
 {'fault':'Reg output forced by external5V/source collapse','behavior':'TPS25810 offstate reverse leakage3uA max to85C atVIN=EN=0; U1 back-to-backFET RCB blocks regulator reverse current towardflex/module. U1reverseleak andresponse typical-only; no zero-backfeed or maxinjectedcharge guarantee.'},
 {'fault':'Reg FBopen/bottomshort','behavior':'U2 internaloutputOVP is described but cannot guarantee USB5.5V limit; U3 AUX/IN2 operating5.5max. D1ESD is not aDCclamp. IndependentUSBoutputOVP not captured, faultvoltageacceptance UNMET.'},
 {'fault':'Module overvoltage','behavior':'IRM20OVP5.75..6.75; U1independentOVLOdiv5.6..5.81 cuts converterinput, response typical-only. No allsinglefault/mainsrelease.'},
 {'fault':'FPCpartialshort/failedtermination','behavior':'U1 is rotating-side, cannot interrupt upstreamFPCshort. Module115..160%overload hiccup not qualifiedFPCprotection. Stationaryfuse/tracefaultcoordination remainsparentintegrationgate.'},
 {'fault':'Detach/brownout','behavior':'U3detaches and dischargesVBUS; U2PG gatesU3EN. PG mayremainhigh down90%output and cannot be promoted to4.75Vsourcevalid. Brownout/reattachraces and actual waveforms unmeasured.'}]
module_body=[52.9,27.7,24.5];coreID=43.;zbottom=-10.75;ztop=zbottom+24.5;radius=math.hypot(27.7/2,max(abs(zbottom),abs(ztop)));radial=coreID/2-radius
assert radial>1.9 and 45+52.9<100 # actual oldPSUboard39..100; no silentextension
# With proposedbodybottom, max4.5mm leads extendpast oldmainskeepouttop-14.5.
leadbottom=zbottom-4.5;trunkclear=leadbottom-(-14.5)
report={'status':'PASS literal/static/conditionalDC checks; source/thermal/USB/fit gates UNMET','IC_pin_checks':sum(len(expected[x]) for x in ['U1','U2','U3']),'USB_physical_terminal_checks':len(expected['J1']),'resistor_checks':len(res),'capacitor_checks':len(caps),'CC_state_rows':states,'regulation':{'nominal_V':5.136,'DC_divider_reference_FBbias_corners_V':[lo,hi],'reference_accuracy_in_forcedPWM':.01,'feedback_leakage_max_A':100e-9,'resistor_initial_plus100K_TCR':tol,'lifetime_drift_included':False,'port_DC_corner_V':[portlo,porthi],'connector_mated_loop_alloc_ohm':connector_loop_alloc,'connector_sharing_guaranteed':False,'extra_line_load_allocation_V':static_extra,'ripple_transient_one_sided_allocation_V':dynamic_allowance,'conditional_port_window_V':[screenlo,screenhi],'not_guaranteed':'Line/load entries0.07%/V,0.2%/A typ-only. No efficiency/ripple/loadstep/headroom guarantee from typicalgraph.'},'input_protection':{'UVLO_rise_V':[min(uv),max(uv)],'UVLO_fall_V':[min(uvfall),max(uvfall)],'OVLO_rise_V':[min(ov),max(ov)],'breaker_A':[min(breaker),max(breaker)],'response_max_s':None,'reverse_current_leakage_max_A':None,'reset':'Externalpowercycle/ENlow for latchedbreaker. Reverseblock is hardware, not software.'},'input_model':{'path_m':length,'hot_copper_R_ohm':flexR,'termination_R_alloc_ohm':termR,'efuse_R_max_ohm':efuseR,'module_instantaneous_voltage_screen_V':[source_min,source_max],'copper_qualified':False,'converter_efficiency_min_published':False,'port_aux_allocation_A':.001,'input_aux_power_alloc_W':.005,'corners':cases,'worst_case':worst,'quad_fixed_point_agreement':True},'current_limit_caveat':'TPS63070 3.05..4.15A guaranteedtabletestVIN5V,VOUT6.5V,Tj0..125; not a guaranteedlimit atactual4.17V input. Table2A is maximumrecommended under statedbuckcondition, not an allcornerdeliverability grant. XFL4.1A10%dropat25C, nohotmin granted.','startup':{'converter_softstart_current_A':'1A typical only untilPG; unknownmaximum','PG_EN_max_low_V':en_low,'PG_EN_min_high_V':en_high,'switched_input_C_nom_uF':30,'bulk_output_C_nom_uF':226.1,'bulk_C_max_tol_uF':271.32,'bulk_polymer_min_25C_uF':120,'filter_effective_C_min_allocation_uF':15.2,'filter_effective_L_max_uH':1.8,'filter_ratio_pass_from_ceramics_alone':False,'note':'76uFceramic at80%effective loss gives15.2uF<18uF ratio target; polymer supplements butfrequency/temperature/ESR mustbequalified. No loop/inrush prooffromtypicalsoftstart.'},'detach':{'RC_discharge_to0p8V_alloc_s':discharge,'minimum_specified_active_discharge_s':.039,'scope':'ConditionalRC beforeextracableC;poweredattachminimumsuppliesneeded. NotUSBtimingcompliance.'},'faults':faults,'stationary_module_geometry':{'part':'IRM-20-5','max_body_mm':module_body,'baseline_core_ID_mm':coreID,'baseline_carrier_x_mm':[39,100],'proposed_body_x_mm':[45,97.9],'proposed_body_z_mm':[zbottom,ztop],'body_to_bore_radial_gap_mm':radial,'lead_length_max_mm':4.5,'max_lead_bottom_z_mm':leadbottom,'gap_to_original_mains_trunk_top_mm':trunkclear,'full_module_carrier_harness_fit':False,'objection':'Bodyfits43mmbore, but maxleads overlap existingmainskeepout by0.75mm in thiszallocation. Parent must reviseinsulation/carrier/harness withoutenlargingcore; no completepackingclaim.'},'module_limits':{'IRM20_fullpower5V_temperature_C':45,'IRM20_fullpower_line_VAC':115,'IRM10comparison':'10Wcannotcoverworstconditional11..13Wreginput+FPC; remainshistorical','proposed_study_temperature_C':[0,45],'proposed_study_line_VAC':[115,305],'source_standard_mains_variants':'DistinctPowerCON/TRUE1/NEMA5-15stationaryendcaps remainparent; connectorratingscapline. No routinechoicequestion.','thermal':'IRM20eff79%typ at5V only; source/inductor/flex/controller/enclosureheating stillunqualified. Freeaircurvesdonotqualifysealedbarrel.'},'protection_frozen':True,'manufacturing_release':False}
assert not any(sh['violations'] for sh in json.loads((P/'erc.json').read_text())['sheets'])
(P/'electrical-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','IC_pin_checks','USB_physical_terminal_checks','resistor_checks','capacitor_checks','regulation','input_protection','stationary_module_geometry']},indent=2));print('Worstinput',worst)
