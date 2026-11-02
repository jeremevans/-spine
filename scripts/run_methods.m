function run_methods(input_file, output_file)
% Native MATLAB/Octave linear interpolation and explicit shared Gaussian formula.
  root=fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root,'matlab'));
  data=jsondecode(fileread(input_file)); cases=data.payload.cases;
  if exist('OCTAVE_VERSION','builtin'), engine='Octave'; else, engine='MATLAB'; end
  rows=cell(numel(cases),1);
  for k=1:numel(cases)
    if iscell(cases), c=cases{k}; else, c=cases(k); end
    q=c.queries;
    if strcmp(c.kind,'scattered')
      d=numel(c.bandwidth); if d==1, q=q(:); end
      y=nadaraya_watson(c.points,c.values,q,c.bandwidth);
    else
      axes=c.axes; if ~iscell(axes), axes=num2cell(axes,2); end
      if numel(c.shape)==1, q=q(:); end
      if ischar(c.fill) || isstring(c.fill), fill=NaN; else, fill=c.fill; end
      y=interpolate_surface(axes,c.values,q,c.method,c.bandwidth,fill);
    end
    rows{k}=struct('name',c.name,'values',y(:)');
  end
  out=struct('engine',engine,'engine_version',version(),'fixture_id',data.fixture_id,'results',{rows});
  parent=fileparts(output_file); if ~exist(parent,'dir'), mkdir(parent); end
  fid=fopen(output_file,'w'); assert(fid>=0); cleanup=onCleanup(@()fclose(fid));
  fprintf(fid,'%s\n',jsonencode(out));
end
