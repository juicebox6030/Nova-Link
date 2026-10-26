"""Kinematic path family; not elastic equilibrium or qualified flex hardware."""
from pathlib import Path
import json, math
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import betainc, betaln
from scipy.spatial import cKDTree

out=Path(__file__).resolve().parent
ri,ro,turns,pitch,thickness=25.,30.5,6.,.30,.16

def curve(n,k,t):
    a,b=2+math.exp(k),2+math.exp(-k)
    remaining=ro-ri-pitch*n
    tt=np.asarray(t)
    clipped=np.clip(tt,1e-12,1-1e-12)
    pdf=np.exp((a-1)*np.log(clipped)+(b-1)*np.log1p(-clipped)-betaln(a,b))
    dpdf=pdf*((a-1)/clipped-(b-1)/(1-clipped))
    radius=ri+pitch*n*tt+remaining*betainc(a,b,tt)
    dr=pitch*n+remaining*pdf
    d2r=remaining*dpdf
    return radius,dr,d2r

def length(n,k):
    theta=2*math.pi*n
    def integrand(t):
        r,dr,_=curve(n,k,t)
        return math.hypot(float(dr),float(r)*theta)
    return quad(integrand,0,1,epsabs=1e-8,epsrel=1e-11,limit=150)[0]

neutral=length(turns,0)
rows=[]
for angle in range(-90,91):
    n=turns+angle/360
    k=brentq(lambda kk:length(n,kk)-neutral,-4,4,xtol=1e-12)
    t=np.linspace(0,1,8193)
    radius,dr,d2r=curve(n,k,t)
    theta=2*math.pi*n
    rp=dr/theta
    rpp=d2r/theta**2
    curvature=np.abs(radius**2+2*rp**2-radius*rpp)/(radius**2+rp**2)**1.5
    bend_radius=1/np.max(curvature)
    xy=np.column_stack([radius*np.cos(theta*t),radius*np.sin(theta*t)])
    distances,indices=cKDTree(xy).query(xy,k=24)
    nonlocal_points=np.abs(indices-np.arange(len(t))[:,None])>100
    nearest=float(np.min(distances[nonlocal_points]))
    segment=float(np.max(np.linalg.norm(np.diff(xy,axis=0),axis=1)))
    # Chord-vs-curve bound to this sampling resolution, not a rigorous global
    # proof between arbitrary angles; all results explicitly kinematic screens.
    interpolation_allowance=2*segment**2/(8*bend_radius)
    gap=nearest-interpolation_allowance-thickness
    assert gap>.10
    assert bend_radius>20
    assert abs(length(n,k)-neutral)<1e-7
    assert abs(float(radius[0])-ri)<1e-9 and abs(float(radius[-1])-ro)<1e-9
    assert abs(float(rp[0])-pitch/(2*math.pi))<1e-9
    assert abs(float(rp[-1])-pitch/(2*math.pi))<1e-9
    rows.append({'angle_deg':angle,'shape_parameter':k,'length_mm':length(n,k),'inner_R_mm':float(radius[0]),'outer_R_mm':float(radius[-1]),'min_bend_R_mm':float(bend_radius),'nearest_nonlocal_sampled_centreline_mm':nearest,'sample_chord_allowance_mm':interpolation_allowance,'screened_turn_surface_gap_mm':gap,'max_segment_mm':segment})
result={'status':'PASS 181-position constant-length kinematic path screen; not equilibrium/cycle validation','neutral_length_mm':neutral,'fixed_end_radii_mm':[ri,ro],'radial_pitch_floor_mm_per_turn':pitch,'allocated_flex_thickness_mm':thickness,'axial_width_mm':20,'end_tangent_radial_slope_mm_per_rad':pitch/(2*math.pi),'max_absolute_length_error_mm':max(abs(x['length_mm']-neutral) for x in rows),'minimum_bend_radius_mm':min(x['min_bend_R_mm'] for x in rows),'minimum_screened_surface_gap_mm':min(x['screened_turn_surface_gap_mm'] for x in rows),'rows':rows,'limits':['A family of geometrically admissible paths with fixed length and fixed end tangent directions; not a passive elastic equilibrium or an actuation/force result.','Dense spatial and 181 angular samples are engineering screens, not continuum contact proof.','No termination/clamp, lock, bearing, USB electronics, connector, material fatigue or manufacturing fit is asserted.']}
(out/'screen.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
