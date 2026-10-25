extern crate ln_decode;
extern crate serde_json;
use ln_decode::analysis_source_mapping::{SourceIdentity,SourceMapping};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::reader_contract::{FragmentRef,ReaderRecordIndex};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{capture,Limits};
use ln_decode::npa_analysis_records::analyze_document;
use ln_decode::npa_context_records::build_context_records;
use ln_decode::npa_analysis_wire::{render_npa_analysis_with_context,recompute_analysis_seals,AnalysisEnvelopeRequest,AnalysisLimits,AnalysisScope};
use ln_decode::npa_analysis_verify::verify_npa_analysis_wire;
fn main(){
 let xml=r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Статья 1. Федеральный закон от 05.04.2013 № 44-ФЗ</w:t></w:r></w:p></w:body></w:wordDocument>"#;
 let p=capture(xml.as_bytes(),&Limits::default()).unwrap();
 let i=ReaderRecordIndex::new(p.records()).unwrap(); let projection=build_projection(p.records()).unwrap();
 let id=SourceIdentity::try_new(p.manifest().source.sha256.clone(),p.manifest().source.bytes,"law-nexus/source-package-model/v1".into(),p.footer().records_seal_hash.clone(),p.footer().manifest_hash.clone()).unwrap();
 let v=DocumentVersionRef::try_new("audit-version".into(),"audit-revision".into(),"reader_wordml_profile/v1".into()).unwrap();
 let mut m=SourceMapping::new(id.clone(),v); for t in i.texts(){m.pin_fragment(FragmentRef::from(t.id.as_str()),t.value.clone(),&id).unwrap();}
 let a=analyze_document(&projection,&i,&m).unwrap();let ctx=build_context_records(&a.layout,&m);
 let text=render_npa_analysis_with_context(&AnalysisEnvelopeRequest{analysis:&a,projection:&projection,index:&i,mapping:&m,limits:AnalysisLimits::default(),scope:AnalysisScope::Bounded},&ctx).unwrap();
 println!("baseline_pass={}",verify_npa_analysis_wire(&text,&projection,&i,&m).is_ok());
 for field in ["source","source_revision","document_version_ref","parent"]{
 let mut lines:Vec<String>=text.lines().map(str::to_owned).collect();
 let mut manifest:serde_json::Value=serde_json::from_str(&lines[0]).unwrap();
 match field {"source"=>manifest["source"]["sha256"]=serde_json::json!("0".repeat(64)),"parent"=>manifest["parent"]["manifest_hash"]=serde_json::json!("0".repeat(64)), _=>manifest[field]=serde_json::json!("forged-identity")};
 lines[0]=serde_json::to_string(&manifest).unwrap();let changed=lines.join("\n")+"\n";let seals=recompute_analysis_seals(&changed).unwrap();
 let last=lines.len()-1; let mut footer:serde_json::Value=serde_json::from_str(&lines[last]).unwrap();footer["records_seal_hash"]=serde_json::json!(seals.records_seal_hash);footer["manifest_hash"]=serde_json::json!(seals.manifest_hash);lines[last]=serde_json::to_string(&footer).unwrap();
 let result=verify_npa_analysis_wire(&(lines.join("\n")+"\n"),&projection,&i,&m);println!("tamper_{field}_accepted={} findings={:?}",result.is_ok(),result.err());
 }
 println!("context_records={ctx:?}");
 let controls=r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>статья</w:t><w:tab/><w:t>5</w:t><w:br/><w:t>часть</w:t><w:tab/><w:t>2</w:t></w:r></w:p></w:body></w:wordDocument>"#;
 let p2=capture(controls.as_bytes(),&Limits::default()).unwrap();let i2=ReaderRecordIndex::new(p2.records()).unwrap();let pr2=build_projection(p2.records()).unwrap();
 let layout=ln_decode::npa_analysis_records::build_analysis_block_layout(&pr2,&i2).unwrap();
 let block_texts:Vec<&str>=layout.blocks.iter().map(|b|b.text.as_str()).collect();
 println!("control_analysis_texts={block_texts:?}");
 assert_eq!(block_texts,["статья\t5\nчасть\t2"],"F02: derived separators must survive into the analysis block text");
}
