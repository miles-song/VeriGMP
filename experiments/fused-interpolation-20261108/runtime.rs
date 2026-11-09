//! Unverified fixture driver. Arithmetic uses the frozen producer; no timings here.
use std::{env,fs,panic::{catch_unwind,AssertUnwindSafe}};
use verigmp::{arithmetic,fast_multiply,toom_multiply,toom_square,toom_words};
#[link(name="gmp")]
unsafe extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
const CANARY:u64=0x7a90_2f61_b38d_45ce;
struct Reader {bytes:Vec<u8>,at:usize}
impl Reader {
    fn word(&mut self)->u64 {
        let value=u64::from_le_bytes(self.bytes[self.at..self.at+8].try_into().unwrap());
        self.at+=8;value
    }
    fn vector(&mut self)->Vec<u64> {(0..self.word()).map(|_|self.word()).collect()}
}
fn guarded(values:&[u64])->Vec<u64> {
    let mut out=Vec::with_capacity(values.len()+2);out.push(CANARY);
    out.extend_from_slice(values);out.push(CANARY);out
}
fn middle(values:&mut[u64])->&mut[u64] {let n=values.len();&mut values[1..n-1]}
fn canaries(values:&[u64]) {assert_eq!(values.first(),Some(&CANARY));assert_eq!(values.last(),Some(&CANARY));}
#[cfg(not(baseline))]
fn helper(dst:&mut[u64],rhs:&[u64],shift:u32) {toom_words::sub_shifted_exact(dst,rhs,shift);}
#[cfg(baseline)]
fn helper(dst:&mut[u64],rhs:&[u64],shift:u32) {
    assert!(shift==1 || shift==4);assert!(dst.len()>=rhs.len());
    let mut scratch=vec![u64::MAX;dst.len()];
    toom_words::copy_pad(&mut scratch,rhs);toom_words::scale_exact(&mut scratch,1u64<<shift);
    toom_words::sub_exact(dst,&scratch);
}
fn invalid_boundaries() {
    std::panic::set_hook(Box::new(|_|{}));
    for (shift,n,m) in [(0,2,1),(2,2,1),(63,2,1),(64,2,1),(u32::MAX,2,1),(1,1,2),(4,0,1)] {
        let mut out=guarded(&vec![31;n]);let before=out.clone();let rhs=vec![1;m];
        assert!(catch_unwind(AssertUnwindSafe(||helper(middle(&mut out),&rhs,shift))).is_err());
        assert_eq!(out,before,"helper must reject before writes");
    }
    for id in 0..8 {
        let mut p1=guarded(&vec![0;2]);let mut pm=guarded(&vec![0;if id==0 {1}else{2}]);
        let mut p2=guarded(&vec![0;if id==1 {1}else{2}]);
        let z0=vec![0;if id==4 {3}else{2}];let z4=vec![0;if id==5 {3}else{2}];
        let mut work=guarded(&vec![93;if id==2 {1}else if id==3 {3}else{2}]);
        let original=(p1.clone(),pm.clone(),p2.clone(),work.clone());
        let (first,second)=if id==6 {(&z0,&z0)}else{(&z0,&z4)};
        // IDs 6/7 are legal repeated immutable inputs and zero signed evaluation.
        let result=catch_unwind(AssertUnwindSafe(||fused_bridge::interpolate(
            middle(&mut p1),middle(&mut pm),middle(&mut p2),first,second,id==7,
            middle(&mut work),&[],&[],&[])));
        if id<6 {assert!(result.is_err());assert_eq!((p1,pm,p2,work),original);}
        else {assert!(result.is_ok());for buffer in [&p1,&pm,&p2,&work] {canaries(buffer);}}
    }
    for n in [0,1,usize::MAX/12,usize::MAX/12+1,usize::MAX/10,usize::MAX/10+1,usize::MAX] {
        assert_eq!(arithmetic::workspace_len(n),if n>0 && n<=usize::MAX/12 {Some(12*n)}else{None});
        assert_eq!(arithmetic::square_workspace_len(n),if n>0 && n<=usize::MAX/10 {Some(10*n)}else{None});
    }
}
fn main() {
    let bytes=fs::read(env::args().nth(1).expect("fixture path")).unwrap();
    assert_eq!(&bytes[..8],b"VGMPFSH1");let mut reader=Reader{bytes,at:8};let count=reader.word();
    for expected_id in 0..count {
        let id=reader.word();assert_eq!(id,expected_id);let op=reader.word();let param=reader.word();
        let top=reader.word() as u32;let extra=reader.word() as usize;let shared=reader.word()!=0;
        let values:Vec<Vec<u64>>=(0..reader.word()).map(|_|reader.vector()).collect();let original=values.clone();
        if op==0 {
            let mut out=guarded(&values[0]);helper(middle(&mut out),&values[1],param as u32);
            assert_eq!(middle(&mut out),values[2],"helper case {id}");canaries(&out);
            // Legal disjoint mutable/immutable regions in one allocation.
            let n=values[0].len();let m=values[1].len();
            let mut joined=vec![CANARY;n+m+3];joined[1..n+1].copy_from_slice(&values[0]);
            joined[n+2..n+m+2].copy_from_slice(&values[1]);
            let (left,right)=joined.split_at_mut(n+2);
            helper(&mut left[1..n+1],&right[..m],param as u32);
            assert_eq!(&left[1..n+1],values[2]);assert_eq!(left[0],CANARY);
            assert_eq!(left[n+1],CANARY);assert_eq!(&right[..m],values[1]);assert_eq!(right[m],CANARY);
        }else if op==1 {
            let n=values[5].len();let mut p1=guarded(&values[5]);let mut pm=guarded(&values[6]);
            let mut p2=guarded(&values[7]);let mut work=guarded(&vec![u64::MAX;n]);
            fused_bridge::interpolate(middle(&mut p1),middle(&mut pm),middle(&mut p2),
                &values[0],&values[4],param!=0,middle(&mut work),&values[1],&values[2],&values[3]);
            assert_eq!(middle(&mut p1),values[8],"coefficient 1 case {id}");
            assert_eq!(middle(&mut pm),values[9],"coefficient 2 case {id}");
            assert_eq!(middle(&mut p2),values[10],"coefficient 3 case {id}");
            for buffer in [&p1,&pm,&p2,&work] {canaries(buffer);}
        }else {
            let a=&values[0];let b=if shared {a}else{&values[1]};let n=a.len();
            let capacity=match op {2|4=>12*n,3|5=>10*n,6=>3*n,_=>panic!("operation")};
            let mut out=guarded(&vec![u64::MAX;values[2].len()]);
            let mut work=guarded(&vec![u64::MAX;capacity+extra]);
            match op {
                2=>arithmetic::mul_mod(middle(&mut out),a,b,middle(&mut work),top),
                3=>arithmetic::square_mod(middle(&mut out),a,middle(&mut work),top),
                4=>toom_multiply::full(middle(&mut out),a,b,middle(&mut work),param as usize),
                5=>toom_square::full(middle(&mut out),a,middle(&mut work),param as usize),
                6=>fast_multiply::full(middle(&mut out),a,b,middle(&mut work),param as usize),
                _=>unreachable!(),
            }
            assert_eq!(middle(&mut out),values[2],"full/default case {id}");canaries(&out);canaries(&work);
            let mut gmp=vec![0u64;2*n];
            unsafe {
                if op==3 || op==5 {__gmpn_sqr(gmp.as_mut_ptr(),a.as_ptr(),n as isize);}
                else {__gmpn_mul_n(gmp.as_mut_ptr(),a.as_ptr(),b.as_ptr(),n as isize);}
            }
            if op==2 || op==3 {gmp.truncate(n);if top<64 {gmp[n-1]&=(1u64<<top)-1;}}
            assert_eq!(gmp,values[2],"GMP control case {id}");
        }
        assert_eq!(values,original,"read-only inputs changed case {id}");
    }
    assert_eq!(reader.at,reader.bytes.len());invalid_boundaries();
    println!("passed {count} independent Python integer fixtures, input preservation, capacity and canary boundaries");
}
