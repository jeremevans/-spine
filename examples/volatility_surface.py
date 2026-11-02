#!/usr/bin/env python3
"""Visualize a synthetic IV surface and actual recorded cross-engine errors."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from spline_equivalence import interpn_spline
from verify import read_fixtures,inputs,validate_engine


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,default=ROOT/'results')
    args=ap.parse_args();out=args.results.resolve();out.mkdir(parents=True,exist_ok=True)
    fixtures=read_fixtures();c=next(c for c in fixtures['payload']['cases'] if c['name']=='volatility_surface')
    axes,v,q,_=inputs(c);shape=c['query_shape']
    fitted=interpn_spline(axes,v,q).reshape(shape,order='F')
    if not (fitted>0).all():raise RuntimeError('Nonpositive IV: real log is undefined')
    surfaces={'Python':fitted};versions=[]
    for engine in ['Octave','R','MATLAB']:
        p=out/(engine.lower()+'.json')
        if p.exists():
            data=json.loads(p.read_text());vals=validate_engine(data,engine,fixtures)
            surfaces[engine]=np.array(vals[c['name']],float).reshape(shape,order='F')
            versions.append(engine+' '+data['engine_version'])
    M=q[:,0].reshape(shape,order='F');T=q[:,1].reshape(shape,order='F')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(13.6,8.7),facecolor='#fafbfd')
    fig.suptitle('A single not-a-knot spline, evaluated across languages',x=.055,ha='left',fontsize=21,fontweight='bold',y=.975,color='#172b45')
    fig.text(.055,.927,'Synthetic implied volatility • 7 × 6 input grid → 81 × 61 query grid • interpolate, then log',fontsize=11,color='#42556b')
    gs=fig.add_gridspec(2,2,left=.07,right=.94,bottom=.12,top=.86,hspace=.48,wspace=.3)
    ax=fig.add_subplot(gs[0,0]);im=ax.pcolormesh(M,T,100*fitted,shading='auto',cmap='viridis')
    gm,gt=np.meshgrid(*axes,indexing='ij');ax.scatter(gm,gt,s=12,c='white',edgecolors='#24354b',linewidths=.5)
    fig.colorbar(im,ax=ax,label='Implied volatility (%)');ax.set(xlabel='Strike / spot',ylabel='Maturity (years)',title='Spline surface; white dots are input nodes')
    ax=fig.add_subplot(gs[0,1]);idx=15
    styles={'Python':dict(color='#176aa6',lw=3),'Octave':dict(color='#d05f22',lw=2,ls='--'),'R':dict(color='#146c43',lw=1.5,ls=':'),'MATLAB':dict(color='#7f378b',lw=1.5,ls='-.')}
    for name,arr in surfaces.items():ax.plot(M[:,idx],100*arr[:,idx],label=name,**styles[name])
    ax.set(xlabel='Strike / spot',ylabel='Implied volatility (%)',title=f'Overlapping curves at maturity {T[0,idx]:.2f} years');ax.legend(frameon=False);ax.grid(alpha=.15)
    ax=fig.add_subplot(gs[1,0])
    others=[abs(arr-fitted) for name,arr in surfaces.items() if name!='Python']
    delta=np.max(others,axis=0) if others else np.zeros_like(fitted)
    im=ax.pcolormesh(M,T,delta*1e15,shading='auto',cmap='magma',vmin=0,vmax=max(.01,float(delta.max()*1e15)))
    fig.colorbar(im,ax=ax,label='Absolute IV difference × 10¹⁵');ax.set(xlabel='Strike / spot',ylabel='Maturity (years)',title='Largest measured difference from Python')
    ax=fig.add_subplot(gs[1,1]);ax.axis('off')
    summary=[f'Engines plotted: {", ".join(surfaces)}',f'Maximum surface difference: {delta.max():.3e}',f'Minimum interpolated IV: {fitted.min():.4f}',f'Log surface is finite: {np.isfinite(np.log(fitted)).all()}','','MATLAB is shown only when actual output is supplied.','This synthetic example is not an arbitrage-free model.']
    for i,line in enumerate(summary):ax.text(0,1-i*.125,line,transform=ax.transAxes,fontsize=11,color='#253b51',va='top')
    fig.text(.07,.035,'Fixed fixtures and native outputs are included. The proof explains equality in exact arithmetic; the plots show measured floating-point agreement.',fontsize=9,color='#526479')
    fig.savefig(out/'volatility_surface.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    np.savez_compressed(out/'volatility_surface.npz',moneyness=M,maturity=T,iv=fitted,log_iv=np.log(fitted))
    print(json.dumps({'engines':list(surfaces),'max_surface_difference':float(delta.max()),'figure':str(out/'volatility_surface.png')},indent=2))


if __name__=='__main__':main()
