% Same exact worked example, using MATLAB or Octave native interpn.
x=[0 1 2 4 7]; y=[-2 0 1 3 4 6];
[i,j]=ndgrid(0:4,0:5);
V=(10+mod((i+2).*(j+3),11))/100;
q=[1.5 .5; 3.25 2.5; 6.75 5.5];
actual=zeros(3,1);
for k=1:3
    actual(k)=interpn(x,y,V,q(k,1),q(k,2),'spline',NaN);
end
expected=[838733/5632000;2031089/13926400;10632481/69632000];
assert(all(abs(actual-expected)<2e-14+2e-13*abs(expected)));
format long g
disp(actual)
