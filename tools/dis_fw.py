import sys
from capstone import *
d=open('D11_H_4.28_original.bin','rb').read()[28:]
BASE=0x01010000
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS); md.detail=False
def dis(va,n=0x100):
    off=va-BASE
    for i in md.disasm(d[off:off+n],va):
        print(f"{i.address:08x}: {i.bytes.hex():8s} {i.mnemonic} {i.op_str}")
if __name__=='__main__':
    dis(int(sys.argv[1],16),int(sys.argv[2],16))
