"""Independent TPS2116 behavioral regression, not imported from the generator.

Primary: cached TI SLVSFG1A, sections 6.1/6.3/6.5/7.3.1/7.3.2/7.4.
Topology matters: MODE physically tied VIN1 is priority mode, not the
external-bias manual mode evaluated merely at the same instantaneous voltage.
This is a steady-state selection proof, not a startup/time-domain simulator.
"""
from pathlib import Path
from itertools import product
import hashlib,json,xml.etree.ElementTree as E

P=Path(__file__).resolve().parent
UNSPEC='unspecified';OFF='unpowered';Z='Hi-Z'

def select(configuration,vin1,vin2,pr_high,mode_v=None):
    """Literal seven rows of TI 7.3.1; do not fill unspecified conditions."""
    if max(vin1,vin2)==0:return OFF
    if max(vin1,vin2)<1.6:return UNSPEC
    if max(vin1,vin2)>5.5:return UNSPEC
    if pr_high is None:return UNSPEC
    if configuration=='MODE=VIN1':
        chosen='VIN1' if pr_high else 'VIN2'
    elif configuration=='external':
        if mode_v is None or not 0<=mode_v<=5.5:return UNSPEC
        if mode_v>=1:chosen='VIN1' if pr_high else 'VIN2'
        elif mode_v<=.35:
            if pr_high:return Z
            if vin1==vin2:return UNSPEC
            chosen='VIN1' if vin1>vin2 else 'VIN2'
        else:return UNSPEC
    else:raise AssertionError(configuration)
    return chosen if (vin1 if chosen=='VIN1' else vin2)>=1.6 else UNSPEC

def u40_selection(pins,vin1,vin2,pr_high):
    if pins['U40.5']==pins['U40.3']:
        return select('MODE=VIN1',vin1,vin2,pr_high)
    if pins['U40.5']=='GND_USB':
        return select('external',vin1,vin2,pr_high,0)
    raise AssertionError('Unvalidated U40 MODE topology')

def run():
    tree=E.parse(P/'qualified15.net')
    pins={p.attrib['ref']+'.'+p.attrib['pin']:n.attrib['name'].rsplit('/',1)[-1] for n in tree.findall('./nets/net') for p in n}
    cs={c.attrib['ref']:c for c in tree.findall('./components/comp')}
    roles={c.findtext('./fields/field[@name="Role"]'):r for r,c in cs.items()}
    def resistor(role):
        import re
        return float(re.search(r' ([\d.]+)ohm',cs[roles['R_'+role]].findtext('value'))[1])
    assert pins['U40.3']==pins['U40.5']=='AON_USB_LIMITED'
    assert pins['U40.4']=='AON_PRIORITY' and pins['U40.6']=='BOOST_3V9'
    assert pins['U7.1']==pins['U7.3']=='AON_RAW'
    assert pins[roles['R_AON_FEED']+'.1']=='VBUS_RAW'
    assert pins[roles['R_AON_FEED']+'.2']==pins['U40.3']
    assert (resistor('AON_FEED'),resistor('AON_PRIORITY_TOP'),resistor('AON_PRIORITY_BOTTOM'))==(330,22100,10000)
    # Complete documented table, each row independently exercised.
    fixtures=[('MODE=VIN1',4.4,0,True,None,'VIN1'),
              ('MODE=VIN1',0,3.9,False,None,'VIN2'),
              ('external',4.4,0,True,2.5,'VIN1'),
              ('external',0,3.9,False,2.5,'VIN2'),
              ('external',4.4,3.9,True,0,Z),
              ('external',4.4,3.9,False,0,'VIN1'),
              ('external',0,3.9,False,0,'VIN2')]
    for cfg,a,b,pr,m,want in fixtures:assert select(cfg,a,b,pr,m)==want
    assert select('external',4.4,3.9,False,.6)==UNSPEC
    assert select('external',4.4,4.4,False,0)==UNSPEC
    assert select('MODE=VIN1',0,0,False)==OFF
    assert select('MODE=VIN1',2.8,0,False)==UNSPEC
    tol=.001+100*25e-6
    thresholds=[];pr_at_source=[];qualified=[]
    for a,b,ileak,vref in product((-tol,tol),(-tol,tol),(-.1e-6,.1e-6),(.92,1.08)):
        top=resistor('AON_PRIORITY_TOP')*(1+a);bot=resistor('AON_PRIORITY_BOTTOM')*(1+b)
        thresholds.append(vref*(1+top/bot)+ileak*top)
        vin=4.4-.002*resistor('AON_FEED')*(1+tol)
        pr=(vin-ileak*top)/(1+top/bot);pr_at_source.append(pr)
        assert pr>vref
        for boost in [0,3.8,4.1]:
            got=u40_selection(pins,vin,boost,pr>vref)
            assert got=='VIN1';qualified.append(got)
    # Old physical wiring as a mutation: don't mutate the expected result.
    old=dict(pins);old['U40.5']='GND_USB'
    vin=4.4-.002*330*(1+tol)
    negative=[]
    for label,boost in [('valid-source empty-cap coldboot',0),('valid-source hotattach',3.9)]:
        before=u40_selection(old,0,boost,False)
        bad=u40_selection(old,vin,boost,True)
        fixed=u40_selection(pins,vin,boost,True)
        assert bad==Z and fixed=='VIN1'
        negative.append({'scenario':label,'old_before':before,'old_after':bad,'fixed_after':fixed,'old_guaranteed_AON_path':False})
    # Every combination of absent/low/priority-valid raw and absent/valid boost.
    states=[]
    for vin,boost in product([0,1.5,2.8,3.6,vin,5.5],[0,1.5,3.8,4.1]):
        # Representative values are strictly outside the entire threshold range.
        high=vin>max(thresholds)
        assert high or vin<min(thresholds)
        got=u40_selection(pins,vin,boost,high)
        if high:assert got=='VIN1'
        elif boost>=1.6:assert got=='VIN2'
        else:assert got in [OFF,UNSPEC]
        states.append({'VIN1_V':vin,'boost_V':boost,'selection':got})
    # MODE and PR1 pin loads added by this correction are bounded by 6.5.
    # IQ max4.4uA at VIN1>VIN2+.1; max4.5uA VIN2 at reverse condition.
    # Use sum of both maxima +2.1uA standby + .1uA each pin conservatively.
    # This is a small specified part of the pre-existing 2mA total allocation.
    divider_max=5.5/((22100+10000)*(1-tol))
    mux_control_max=4.4e-6+4.5e-6+2.1e-6+2*.1e-6
    load_limit=(4.4-max(thresholds))/(330*(1+tol))
    assert divider_max+mux_control_max<.000184
    assert .002<load_limit
    assert vin<=5.5 and 5.5*10000*(1+tol)/(22100*(1-tol)+10000*(1+tol))<5.5
    # Main mux may select VIN1 early; it is NOT an off-state barrier.
    assert pins['U19.5']=='AON_2V5' and pins['U19.4']=='SOURCE_VALID'
    main=[]
    for mode in [0,.2,.35,.6,1,1.65,2.5]:
        for pr in [False,True]:
            got=select('external',4.4,0,pr,mode)
            if mode<=.35:assert got==(Z if pr else 'VIN1')
            if .35<mode<1:assert got==UNSPEC
            if mode>=1:assert got==('VIN1' if pr else UNSPEC)
            main.append({'AON_MODE_V':mode,'PR1_high':pr,'empty_cap_selection':got})
    datasheet=P.parents[1]/'source-cache/tps2116.pdf'
    txt=P.parents[1]/'source-cache/tps2116.txt'
    assert hashlib.sha256(datasheet.read_bytes()).hexdigest()=='5babd88afb84e2e65c9c0da23b75f85758c0c730e34102a0fb746ac9573ed1d5'
    report={'status':'PASS source-table/topology/DC regression; no transient guarantee',
      'primary':{'document':'TI SLVSFG1A May2021','pdf':str(datasheet.relative_to(P.parents[4])),
                 'pdf_sha256':hashlib.sha256(datasheet.read_bytes()).hexdigest(),'text_sha256':hashlib.sha256(txt.read_bytes()).hexdigest(),
                 'sections':'6.1 absolute controls -0.3..6V; 6.3 inputs1.6..5.5V controls0..5.5V; 6.5 leakage/IQ/VREF; 7.3.1 seven truth rows; 7.3.2 softstart; 7.4 collapse',
                 'cached_text_line_ranges':{'absolute':[116,125],'operating':[153,164],'truth_table':[583,603]}},
      'documented_truth_rows_tested':len(fixtures),'qualified_source_corner_cases':len(qualified),
      'raw_boost_cases':states,'old_wiring_negative_regressions':negative,
      'priority_input_threshold_min_V':min(thresholds),'priority_input_threshold_max_V':max(thresholds),
      'qualified_raw_V':4.4,'total_AON_feed_allocation_A':.002,
      'AON_VIN1_min_under_allocation_V':4.4-.002*330*(1+tol),'PR1_min_under_allocation_V':min(pr_at_source),
      'priority_load_at_threshold_max_A':load_limit,'divider_max_A':divider_max,
      'conservative_mux_IQ_standby_control_sum_A':mux_control_max,
      'remaining_2mA_allocation_for_LDO_logic_pullups_A':.002-divider_max-mux_control_max,
      'main_U19_ramp_states':main,
      'limitations':['2mA total steady AON load is an engineering allocation, not a measured or full switching-current maximum. Separate max IQ values retain their TI test conditions.',
        'Selected input below1.6V, equal inputs in manual low mode, PR1 at threshold and MODE external .35..1V have no table guarantee.',
        'U19 may feed BACKUP_RAW early while MODE low; source qualification/buck enable are separate. AON gates below1.65V remain unspecified.',
        'U40 priority is raw-fed before AON exists; no self-powered external MODE bias. Cold startup U40 output softstart current/time maximum unspecified.',
        'Switching/RCB/hold-up, fast raw collapse per7.4, ramp, loadsteps, ESR and thermal require bench validation. No startup gate closed.'],
      'manufacturing_release':False}
    (P/'mux-mode-proof.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    result=run()
    print(json.dumps({k:result[k] for k in ['status','documented_truth_rows_tested','qualified_source_corner_cases','old_wiring_negative_regressions','priority_input_threshold_max_V','AON_VIN1_min_under_allocation_V','priority_load_at_threshold_max_A']},indent=2))
