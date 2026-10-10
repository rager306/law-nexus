//! One tracked Consultant WordML fixture, not corpus-wide or Garant evidence.
//! The slot-sequence pin was cross-checked against an external Expat event
//! oracle; this test keeps that bounded characterization, not legal gold.
use ln_decode::source_package::{Limits, Record, capture, read_package, write_package};
use sha2::{Digest, Sha256};
use std::{fs, io::Cursor, path::Path};

#[test]
fn tracked_wordml_roundtrip_keeps_oracle_checked_text_slots() {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml");
    let xml = fs::read(path).expect("read tracked bounded WordML fixture");
    assert_eq!(xml.len(), 193_726);
    assert_eq!(
        format!("{:x}", Sha256::digest(&xml)),
        "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d"
    );
    let limits = Limits::default();
    let package = capture(&xml, &limits).expect("capture real fixture");
    let mut elements = 0;
    let mut slots = 0;
    let mut text_bytes = 0;
    let mut slot_hash = Sha256::new();
    for record in package.records() {
        match record {
            Record::Element(_) => elements += 1,
            Record::Text(text) => {
                slots += 1;
                text_bytes += text.value.len();
                for value in [text.owner.as_str(), text.slot.as_str(), text.value.as_str()] {
                    slot_hash.update((value.len() as u64).to_be_bytes());
                    slot_hash.update(value.as_bytes());
                }
            }
        }
    }
    assert_eq!((elements, slots, text_bytes), (3167, 295, 96_161));
    assert_eq!(
        format!("{:x}", slot_hash.finalize()),
        "9bf5339d3151bef78bc84928a1236172a09611d0feb19319db50d7fe00c29672"
    );
    let mut first = Vec::new();
    write_package(&package, &mut first, &limits).expect("export");
    let restored = read_package(Cursor::new(&first), &limits).expect("read verified package");
    assert_eq!(package, restored);
    let mut second = Vec::new();
    write_package(&restored, &mut second, &limits).expect("repeat export");
    assert_eq!(first, second, "deterministic repeat output");
}
