#!/usr/bin/env python3
"""Compare three methods on identical synthetic IV observations; interpolate, then log."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from spline_equivalence import interpolate_surface


def truth(m,t):
    return .18+.05*np.exp(-t)+.2*(m-1)**2-.06*(m-1)+.008*np.sin(7*m)*np.exp(-t/2)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'results/method-comparison')
    ap.add_argument('--bandwidth',nargs=2,type=float,default=[.09,.35],metavar=('MONEYNESS','YEARS'))
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    axes=[np.array([.7,.85,.95,1.05,1.2,1.35]),np.array([.05,.25,.5,1.,2.,3.])]
    gm,gt=np.meshgrid(*axes,indexing='ij')
    values=truth(gm,gt)+np.random.default_rng(211).normal(0,.004,gm.shape)
    m=np.linspace(axes[0][0],axes[0][-1],101);t=np.linspace(axes[1][0],axes[1][-1],81)
    M,T=np.meshgrid(m,t,indexing='ij');q=np.column_stack([M.ravel(),T.ravel()])
    target=truth(M,T);methods=['spline','linear','nadaraya_watson']
    labels=['Not-a-knot spline','Multilinear','Gaussian Nadaraya–Watson']
    curves={};surfaces={};metrics={};saved=dict(moneyness=M,maturity=T,observed_iv=values,axis_moneyness=axes[0],axis_maturity=axes[1],bandwidth=args.bandwidth,synthetic_truth=target)
    for method in methods:
        kw=dict(method=method,bandwidth=args.bandwidth if method=='nadaraya_watson' else None)
        surface=interpolate_surface(axes,values,q,**kw).reshape(M.shape)
        if not np.isfinite(surface).all() or not (surface>0).all():
            raise RuntimeError(f'{method}: IV must be finite and positive before taking logs')
        surfaces[method]=surface
        curves[method]=interpolate_surface(axes,values,np.column_stack([m,np.full_like(m,.5)]),**kw)
        nodes=np.column_stack([gm.ravel(),gt.ravel()])
        node_error=np.max(abs(interpolate_surface(axes,values,nodes,**kw)-values.ravel()))
        metrics[method]=dict(rmse_to_synthetic_truth=float(np.sqrt(np.mean((surface-target)**2))),max_node_deviation=float(node_error),minimum_iv=float(surface.min()))
        saved[method+'_iv']=surface;saved[method+'_log_iv']=np.log(surface)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(14,8),layout='constrained',facecolor='#fafbfd')
    gs=fig.add_gridspec(2,3,height_ratios=[1,1]);vmin=min(s.min() for s in surfaces.values())*100;vmax=max(s.max() for s in surfaces.values())*100
    for i,(method,label) in enumerate(zip(methods,labels)):
        ax=fig.add_subplot(gs[0,i]);im=ax.pcolormesh(M,T,100*surfaces[method],shading='auto',cmap='viridis',vmin=vmin,vmax=vmax)
        ax.scatter(gm,gt,s=9,color='white',edgecolors='#26364a',linewidths=.3)
        ax.set(title=label,xlabel='Strike / spot',ylabel='Maturity (years)');fig.colorbar(im,ax=ax,label='IV (%)',shrink=.85)
    ax=fig.add_subplot(gs[1,:2]);ax.plot(m,100*truth(m,.5),'k--',lw=1.3,label='Synthetic truth')
    for method,label,color in zip(methods,labels,['#6e43a3','#d87c16','#18798c']):ax.plot(m,100*curves[method],label=label,color=color,lw=2)
    ax.scatter(axes[0],100*values[:,2],color='#172b45',s=22,label='Observed nodes',zorder=5)
    ax.set(title='Same observed data, different fitted curves: maturity 0.5 years',xlabel='Strike / spot',ylabel='IV (%)');ax.legend(frameon=False,ncol=2,fontsize=9);ax.grid(alpha=.15)
    ax=fig.add_subplot(gs[1,2]);ax.axis('off')
    text=['6 × 6 synthetic input grid','Gaussian observation noise: 0.4 IV points','',f'NW bandwidths: {args.bandwidth[0]:g} moneyness',f'                        {args.bandwidth[1]:g} years','','All three fits use the same raw IV.','The natural log is applied after fitting.','','NW smooths; nodes need not match.','Bandwidths here are illustrative.','No arbitrage constraints are imposed.']
    for i,line in enumerate(text):ax.text(0,1-.078*i,line,transform=ax.transAxes,va='top',color='#263b51',fontsize=10)
    fig.suptitle('Choose the surface method explicitly',fontsize=20,fontweight='bold',color='#172b45')
    fig.savefig(out/'comparison.png',dpi=150);plt.close(fig)
    np.savez_compressed(out/'comparison.npz',**saved)
    report=dict(description='Synthetic demonstration; no historical quotes or automatic bandwidth selection',bandwidth=args.bandwidth,metrics=metrics)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
