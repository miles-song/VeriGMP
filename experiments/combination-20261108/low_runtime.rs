//! Correctness and public-boundary driver; no timer is used.
use std::{env,fs,panic::{catch_unwind,AssertUnwindSafe}};
use verigmp::{arithmetic,square_low};
#[link(name="gmp")]
unsafe extern "C" {fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);}
const CANARY:u64=0x32c6_91a4_eb7f_d508;
fn word(data:&[u8],at:&mut usize)->u64 {let out=u64::from_le_bytes(data[*at..*at+8].try_into().unwrap());*at+=8;out}
fn vector(data:&[u8],at:&mut usize,n:usize)->Vec<u64> {(0..n).map(|_|word(data,at)).collect()}
fn boundaries() {
    std::panic::set_hook(Box::new(|_|{}));
    for id in 0..7 {
        let n=if id==0 {0}else{2};let a=vec![1;n];
        let mut out=vec![93;if id==1 {n+1}else if id==2 {n-1}else{n}];
        let mut work=vec![94;if id==3 {10*n-1}else{10*n}];
        let saved=out.clone();let scratch=work.clone();
        let result=catch_unwind(AssertUnwindSafe(||square_low::low(&mut out,&a,&mut work,
            if id==4 {23}else{192},if id==5 {23}else{64},if id==6 {3}else{1})));
        assert!(result.is_err(),"public low-square invalid boundary {id}");
        assert_eq!(out,saved);assert_eq!(work,scratch);
    }
    for top in [0,65] {
        let mut out=[93;2];let mut work=[94;20];
        assert!(catch_unwind(AssertUnwindSafe(||arithmetic::square_mod(&mut out,&[1,2],&mut work,top))).is_err());
        assert_eq!(out,[93;2]);assert_eq!(work,[94;20]);
    }
    for n in [0,1,2,usize::MAX/10,usize::MAX/10+1,usize::MAX] {
        assert_eq!(arithmetic::square_workspace_len(n),if n>0&&n<=usize::MAX/10 {Some(10*n)}else{None});
    }
}
fn main() {
    let data=fs::read(env::args().nth(1).unwrap()).unwrap();assert_eq!(&data[..8],b"VGDLOW01");
    let mut at=8;let count=word(&data,&mut at);
    for id in 0..count {
        let op=word(&data,&mut at);let n=word(&data,&mut at) as usize;
        let threshold=word(&data,&mut at) as usize;let limit=word(&data,&mut at) as usize;
        let split=word(&data,&mut at) as u32;let top=word(&data,&mut at) as u32;let extra=word(&data,&mut at) as usize;
        let a=vector(&data,&mut at,n);let expected=vector(&data,&mut at,n);let saved=a.clone();
        let mut out=vec![CANARY;n+2];let mut work=vec![CANARY;10*n+extra+2];
        if op==0 {square_low::low(&mut out[1..n+1],&a,&mut work[1..10*n+extra+1],threshold,limit,split);}
        else {arithmetic::square_mod(&mut out[1..n+1],&a,&mut work[1..10*n+extra+1],top);}
        assert_eq!(&out[1..n+1],&expected,"Python low-square case {id}");
        let mut exact=vec![0;2*n];unsafe {__gmpn_sqr(exact.as_mut_ptr(),a.as_ptr(),n as isize);}
        exact.truncate(n);if top<64 {exact[n-1]&=(1u64<<top)-1;}
        assert_eq!(exact,expected,"GMP low-square case {id}");assert_eq!(a,saved);
        assert_eq!(out[0],CANARY);assert_eq!(out[n+1],CANARY);
        assert_eq!(work[0],CANARY);assert_eq!(*work.last().unwrap(),CANARY);
    }
    assert_eq!(at,data.len());boundaries();
    println!("passed {count} forced/default Python/GMP squares,9 prewrite panics,6 workspace boundaries");
}
