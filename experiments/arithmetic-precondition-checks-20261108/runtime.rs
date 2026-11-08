//! Unverified correctness driver; GMP FFI is restricted to this test executable.
use std::{env, fs, panic::{catch_unwind, AssertUnwindSafe}};
use verigmp::{arithmetic, fast_multiply, toom_multiply};
#[cfg(not(ordinary_control))]
use verigmp::fast_multiply as full_api;
#[cfg(ordinary_control)]
use verigmp_control as full_api;
#[link(name="gmp")]
unsafe extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
struct Reader { bytes:Vec<u8>, at:usize }
impl Reader {
    fn word(&mut self)->u64 {
        let value=u64::from_le_bytes(self.bytes[self.at..self.at+8].try_into().unwrap());
        self.at+=8;value
    }
    fn vector(&mut self)->Vec<u64> {
        let n=self.word() as usize;(0..n).map(|_|self.word()).collect()
    }
}
const CANARY:u64=0x8a19_30de_5f24_67bc;
fn guarded(n:usize)->Vec<u64> {
    let mut words=vec![u64::MAX;n+2];words[0]=CANARY;words[n+1]=CANARY;words
}
fn middle(words:&mut[u64])->&mut[u64] {let end=words.len()-1;&mut words[1..end]}
fn run(op:u64,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize,top:u32) {
    match op {
        0=>full_api::full(out,a,b,scratch,threshold),
        1=>toom_multiply::full(out,a,b,scratch,threshold),
        2=>fast_multiply::mul_mod(out,a,b,scratch,top),
        3=>arithmetic::mul_mod(out,a,b,scratch,top),
        4=>arithmetic::square_mod(out,a,scratch,top),
        _=>panic!("invalid operation"),
    }
}
fn invalid_boundaries() {
    std::panic::set_hook(Box::new(|_|{}));
    for id in 0..7 {
        let n=if id==0 {0}else{2};
        let a=vec![1;n];let b=vec![2;if id==1 {1}else{n}];
        let out_len=if id==2 {2*n-1}else if id==3 {2*n+1}else{2*n};
        let work_len=if id==4 {3*n-1}else{3*n};
        let mut out=vec![93;out_len];let mut scratch=vec![94;work_len];
        let before_out=out.clone();let before_work=scratch.clone();
        let threshold=if id==5 {0}else if id==6 {7}else{24};
        let result=catch_unwind(AssertUnwindSafe(||full_api::full(
            &mut out,&a,&b,&mut scratch,threshold)));
        assert!(result.is_err(),"invalid public boundary {id} accepted");
        assert_eq!(out,before_out,"output changed before rejection {id}");
        assert_eq!(scratch,before_work,"scratch changed before rejection {id}");
    }
    for n in [0,1,2,usize::MAX/4,usize::MAX/4+1,usize::MAX] {
        assert_eq!(fast_multiply::workspace_len(n),
                   if n>0 && n<=usize::MAX/4 {Some(4*n)}else{None});
    }
}
fn main() {
    let bytes=fs::read(env::args().nth(1).expect("fixture path")).unwrap();
    assert_eq!(&bytes[..8],b"VGMPCHK1");
    let mut reader=Reader{bytes,at:8};let count=reader.word() as usize;
    for expected_id in 0..count {
        let id=reader.word() as usize;assert_eq!(id,expected_id);
        let op=reader.word();let n=reader.word() as usize;
        let threshold=reader.word() as usize;let top=reader.word() as u32;
        let extra=reader.word() as usize;let shared=reader.word()!=0;
        let a=reader.vector();let b=reader.vector();let expected=reader.vector();
        assert_eq!(a.len(),n);assert_eq!(b.len(),n);
        let before_a=a.clone();let before_b=b.clone();
        let factor=match op {0=>3,1|3=>12,2=>4,4=>10,_=>panic!()};
        let mut out=guarded(expected.len());let mut scratch=guarded(factor*n+extra);
        run(op,middle(&mut out),&a,if shared {&a}else{&b},middle(&mut scratch),threshold,top);
        assert_eq!(middle(&mut out),expected,"Python oracle case {id}");
        let mut exact=vec![0u64;2*n];
        unsafe {
            if op==4 {__gmpn_sqr(exact.as_mut_ptr(),a.as_ptr(),n as isize);}
            else {__gmpn_mul_n(exact.as_mut_ptr(),a.as_ptr(),if shared {a.as_ptr()}else{b.as_ptr()},n as isize);}
        }
        if op>1 {exact.truncate(n);if top<64 {exact[n-1]&=(1u64<<top)-1;}}
        assert_eq!(exact,expected,"GMP oracle case {id}");
        assert_eq!(a,before_a,"left changed {id}");assert_eq!(b,before_b,"right changed {id}");
        for buffer in [&out,&scratch] {
            assert_eq!(buffer.first(),Some(&CANARY));assert_eq!(buffer.last(),Some(&CANARY));
        }
    }
    assert_eq!(reader.at,reader.bytes.len());
    invalid_boundaries();
    println!("passed {count} Python/GMP exact cases,7 public panic/preservation and6 workspace boundaries");
}
