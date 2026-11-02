function run_engine(input_file, output_file)
% Actual MATLAB/Octave execution. Base MATLAB; no toolbox required.
% JSON values use MATLAB column-major (Fortran) order.
  if nargin < 1, input_file = 'fixtures/splines.json'; end
  if nargin < 2, output_file = 'results/matlab.json'; end
  data = jsondecode(fileread(input_file));
  if exist('OCTAVE_VERSION','builtin')
    engine = 'Octave';
  else
    engine = 'MATLAB';
  end
  cases = data.payload.cases;
  results = cell(numel(cases),1);
  for k=1:numel(cases)
    if iscell(cases), c = cases{k}; else, c = cases(k); end
    axes = c.axes;
    if ~iscell(axes)
      % JSON decoders may collapse equally sized nested vectors to matrices.
      % MATLAB and Octave both orient JSON nested rows as matrix rows.
      axes = num2cell(axes,2);
    end
    d = numel(c.shape);
    for j=1:d, axes{j}=axes{j}(:); end
    q = c.queries;
    if d==1, q=q(:); end
    query_args = cell(1,d);
    for j=1:d, query_args{j}=q(:,j); end
    if ischar(c.fill) || isstring(c.fill), fill=NaN; else, fill=c.fill; end
    if d==1
      v=c.values(:);
      y=interp1(axes{1},v,q,'spline',fill);
    else
      v=reshape(c.values,c.shape(:)');
      if isfield(c,'query_shape') && ~isempty(c.query_shape)
        for j=1:d, query_args{j}=reshape(q(:,j),c.query_shape(:)'); end
        y=interpn(axes{:},v,query_args{:},'spline',fill);
      elseif strcmp(engine,'Octave')
        % Octave spline interprets vector queries as Cartesian grid vectors.
        % Scalar calls unambiguously test each paired point using native interpn.
        y=zeros(size(q,1),1);
        for p=1:size(q,1)
          for j=1:d, query_args{j}=q(p,j); end
          y(p)=interpn(axes{:},v,query_args{:},'spline',fill);
        end
      else
        y=interpn(axes{:},v,query_args{:},'spline',fill);
      end
    end
    results{k}=struct('name',c.name,'values',y(:)');
  end
  out=struct('schema_version',1,'engine',engine,'engine_version',version(), ...
      'fixture_id',data.fixture_id,'method','not-a-knot tensor spline', ...
      'results',{results});
  parent=fileparts(output_file);
  if ~isempty(parent) && ~exist(parent,'dir'), mkdir(parent); end
  fid=fopen(output_file,'w');
  if fid<0, error('Cannot open output file'); end
  cleanup=onCleanup(@() fclose(fid));
  fprintf(fid,'%s\n',jsonencode(out));
end
