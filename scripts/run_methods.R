#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly=TRUE)
script <- sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
source(file.path(dirname(dirname(normalizePath(script))),'r','interpolate_surface.R'))
data <- jsonlite::fromJSON(args[1],simplifyVector=FALSE)
rows <- lapply(data$payload$cases,function(c) {
  q <- do.call(rbind,lapply(c$queries,unlist)); v <- unlist(c$values)
  h <- unlist(c$bandwidth)
  if (c$kind=='scattered') {
    y <- nadaraya_watson(do.call(rbind,lapply(c$points,unlist)),v,q,h)
  } else {
    fill <- if(is.character(c$fill))NA_real_ else c$fill
    y <- interpolate_surface(lapply(c$axes,unlist),v,q,c$method,h,fill)
  }
  list(name=c$name,values=unname(y))
})
out <- list(engine='R',engine_version=R.version.string,fixture_id=data$fixture_id,results=rows)
dir.create(dirname(args[2]),recursive=TRUE,showWarnings=FALSE)
jsonlite::write_json(out,args[2],auto_unbox=TRUE,digits=17,na='null',pretty=TRUE)
