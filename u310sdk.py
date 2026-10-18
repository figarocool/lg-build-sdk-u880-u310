#!/usr/bin/env python3
"""LG U310 / U880 firmware-specific C to PXO SDK. Never writes USB."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SDK = Path(__file__).resolve().parent
TARGETS = {
    'u310': {'template': SDK/'templates/u310/Calculator.pxo',
             'sha': '46d3749a818934979c89667a363b3cfa871430df4797032190c80b217abd206d',
             'firmware': 'U310 V10a original template', 'define': []},
    'u880': {'template': SDK/'templates/u880/Calculator.pxo',
             'sha': 'f7ddede00f1bf695190ee32738b2d963ba00b7fb52e870eda9702405cb982059',
             'firmware': 'U880 V10b original template', 'define': ['-DU310_TARGET_U880']},
}
TARGET = 'u310'
TEMPLATE = TARGETS['u310']['template']
TEMPLATE_SHA = TARGETS['u310']['sha']
CODE_FILE = 0x104
CODE_END = 0xa3f4   # = template length - 62; U880 is 4 bytes shorter
META = 0xe4


def select_target(name):
    """Switch the template/limits between firmwares (U310 V10a, U880 V10b)."""
    global TARGET, TEMPLATE, TEMPLATE_SHA, CODE_END
    if name not in TARGETS:
        raise ValueError('Unknown target '+name)
    info = TARGETS[name]
    if not info['template'].is_file():
        raise ValueError('Import your original template first: import-template FILE --target '+name)
    data = info['template'].read_bytes()
    if info['sha'] is None:
        info['sha'] = hashlib.sha256(data).hexdigest()
    TARGET, TEMPLATE, TEMPLATE_SHA = name, info['template'], info['sha']
    CODE_END = len(data) - 62


def tool(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise ValueError('Missing tool: '+ ' / '.join(names))


def encode_delta(delta):
    """PXO delta record, code base relocation (flag 0)."""
    if delta < 0:
        raise ValueError('Relocation offsets must be sorted')
    if delta < 32:
        return bytes([delta])
    if delta < 4096:
        return bytes([0x20 | (delta >> 8), delta & 255])
    if delta < 0x80000:
        return bytes([0x30 | (delta >> 16), (delta >> 8) & 255, delta & 255])
    if delta < 0x4000000:
        return bytes([0x38 | (delta >> 24), (delta >> 16) & 255, (delta >> 8) & 255, delta & 255])
    raise ValueError('PXO relocation delta too large')


def text_asset(config, output):
    from PIL import Image, ImageDraw, ImageFont
    width, height = config.get('width',176), config.get('height',40)
    if not 1 <= width <= 255 or not 1 <= height <= 255:
        raise ValueError('Bitmap dimensions must fit one byte')
    symbol = config.get('symbol','hello_bitmap')
    if not symbol.isidentifier() or not symbol.isascii():
        raise ValueError('Invalid C asset symbol')
    font = ImageFont.truetype(config.get('font','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),config.get('font_size',22))
    im = Image.new('RGB',(width,height),'black')
    draw = ImageDraw.Draw(im)
    message=config['text']
    box=draw.textbbox((0,0),message,font=font)
    if box[2]-box[0] > width or box[3] > height:
        raise ValueError('Text does not fit bitmap')
    draw.text(((width-(box[2]-box[0]))//2,3),message,font=font,fill='white')
    pixels = im.get_flattened_data() if hasattr(im, 'get_flattened_data') else im.getdata()
    data=bytes([width,height,16,0])+b''.join(struct.pack('<H',((r>>3)<<11)|((g>>2)<<5)|(b>>3)) for r,g,b in pixels)
    lines=[f'static const unsigned char {symbol}[] __attribute__((aligned(4))) = {{']
    lines += [','.join(f'0x{v:02x}' for v in data[i:i+24])+',' for i in range(0,len(data),24)]
    lines.append('};')
    (output/(symbol+'.h')).write_text('\n'.join(lines)+'\n')


def pack(elf_path, destination, size=None):
    """Pack the linked ELF into the original Calculator PXO4 template.

    Default preserves its length and additive sum. Explicit size grows the
    code allocation and, when necessary, the relocation area. Header offset
    0x0c points at the moved 32-byte descriptor; descriptor word 1 includes
    its own 32 bytes and the code allocation. Other descriptor fields and
    the original 62-byte trailer are preserved. The original container metadata and trailer are retained.
    """
    from elftools.elf.elffile import ELFFile
    from elftools.elf.relocation import RelocationSection
    original=TEMPLATE.read_bytes()
    if hashlib.sha256(original).hexdigest()!=TEMPLATE_SHA:
        raise ValueError('Unsupported or changed original Calculator template')
    grown = size is not None
    if grown and size < len(original):
        raise ValueError('size must be at least the original template length')
    total_size = size if grown else len(original)
    code_end = (total_size - 62) if grown else CODE_END
    with elf_path.open('rb') as handle:
        elf=ELFFile(handle)
        if elf['e_machine']!='EM_ARM' or not elf.little_endian or elf['e_type']!='ET_EXEC':
            raise ValueError('Expected linked little-endian ARM ELF')
        symtab=elf.get_section_by_name('.symtab')
        symbols={s.name:s['st_value'] for s in symtab.iter_symbols()}
        relocations=[]
        # Relative branch relocations were resolved by the linker and remain valid
        # when all application sections move together. Other kinds are rejected.
        position_relative={0,1,3,10,28,29,30,51,102,103}
        for section in elf.iter_sections():
            if not isinstance(section,RelocationSection):
                continue
            target=elf.get_section(section['sh_info'])
            if not target['sh_flags'] & 2:
                continue
            for rel in section.iter_relocations():
                kind=rel['r_info_type']
                if kind==2:
                    symbol=symtab.get_symbol(rel['r_info_sym'])
                    if symbol['st_shndx'] in ('SHN_ABS','SHN_UNDEF'):
                        raise ValueError(f'Absolute/external symbol cannot be rebased: {symbol.name}')
                    relocations.append(rel['r_offset'])
                elif kind not in position_relative:
                    raise ValueError(f'Unsupported ARM relocation {kind} at {rel["r_offset"]:#x}')
        offsets=sorted(set(relocations))
        stream=bytearray(); previous=0
        for address in offsets:
            stream.extend(encode_delta(address-previous));previous=address
        meta=max(META,(0x30+len(stream)+3)&~3) if grown else META
        if len(stream)>meta-0x30:
            raise ValueError(f'Relocation table needs {len(stream)} bytes; use build --size')
        if grown:
            patched=bytearray(total_size)
            patched[:0x30]=original[:0x30]
            patched[meta:meta+0x20]=original[META:CODE_FILE]
        else:
            patched=bytearray(original)
        patched[0x30:meta]=bytes(meta-0x30)
        patched[meta+0x20:code_end]=bytes(code_end-meta-0x20)
        high=0x20
        sections=[]
        code_limit = code_end if grown else CODE_END - META
        for section in elf.iter_sections():
            if not section['sh_flags'] & 2 or not section['sh_size']:
                continue
            start=section['sh_addr']; end=start+section['sh_size']
            if start < 0x20 or meta+end>code_limit:
                raise ValueError('App exceeds this template\'s code allocation')
            high=max(high,end)
            sections.append({'name':section.name,'address':start,'size':section['sh_size']})
            if section['sh_type']!='SHT_NOBITS':
                offset=meta+start
                patched[offset:offset+section['sh_size']]=section.data()
        for address in offsets:
            if address%4 or address < 0x20 or address+4>high:
                raise ValueError('Invalid/unaligned relocation target')
        patched[0x30:0x30+len(stream)]=stream
        struct.pack_into('<I',patched,0x10,len(offsets))
        for offset,name in ((24,'pxo_init'),(28,'pxo_entry')):
            value=symbols.get(name,0)
            if not value & 1 or not 0x20<=value<high:
                raise ValueError(f'Missing Thumb entry point: {name}')
            struct.pack_into('<I',patched,meta+offset,value)
        if grown:
            struct.pack_into('<I',patched,0x0c,meta)
            struct.pack_into('<I',patched,meta+4,code_end-meta)
            struct.pack_into('<I',patched,0x08,total_size)      # word[2]: total file length
            struct.pack_into('<I',patched,0x2c,code_end+12)     # word[11]: CODE_END+12 (verified pattern)
            patched[total_size-62:total_size]=original[-62:]    # original's own trailer, verbatim, relocated
            destination.write_bytes(patched)
            report={'format':'PXO4','slot':'Calculator.pxo','firmware':TARGETS[TARGET]['firmware'],'target':TARGET,'grown':True,
                    'size':len(patched),'sha256':hashlib.sha256(patched).hexdigest(),
                    'sum32':hex(sum(patched)&0xffffffff),'app_memory_used':high,'sections':sections,
                    'entry':symbols['pxo_entry'],'initializer':symbols['pxo_init'],
                    'relocation_offsets':offsets,'relocation_stream_bytes':len(stream),
                    'metadata_offset':meta,'code_end':code_end,'hardware_tested':False}
            destination.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
            return report
        padding_begin=(META+high+3)&~3
        delta=sum(original)-sum(patched)
        capacity=(CODE_END-padding_begin)*255
        if delta<0 or delta>capacity:
            raise ValueError('App leaves insufficient unused space to preserve the MODULE checksum; smaller app required')
        for i in range(padding_begin,CODE_END):
            patched[i]=min(delta,255);delta-=patched[i]
        if delta or len(patched)!=len(original) or sum(patched)!=sum(original):
            raise ValueError('PXO checksum construction failed')
        destination.write_bytes(patched)
        report={'format':'PXO4','slot':'Calculator.pxo','firmware':TARGETS[TARGET]['firmware'],'target':TARGET,
                'size':len(patched),'sha256':hashlib.sha256(patched).hexdigest(),
                'sum32':hex(sum(patched)),'app_memory_used':high,'sections':sections,
                'entry':symbols['pxo_entry'],'initializer':symbols['pxo_init'],
                'relocation_offsets':offsets,'relocation_stream_bytes':len(stream),
                'checksum_padding_begin':padding_begin,'hardware_tested':False}
        destination.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
        return report


def grown_version_file(payload, base=None):
    """Version with Calculator.pxo's checksum updated to match a grown payload.

    The checksum is a plain additive byte sum (not a crypto hash).
    """
    # Other firmwares: locate the record by its path instead of a fixed offset.
    if base is None:
        base=TEMPLATE.parent/'Version'
    version=bytearray(base.read_bytes())
    names=(b'/UPLOAD/Pxo/Calculator.pxo\0',b'/LGAPP/Pxo/Calculator.pxo\0')
    if sum(version.count(name) for name in names)!=1:
        raise ValueError('Calculator.pxo record not found once in Version')
    name=next(name for name in names if name in version)
    struct.pack_into('<I',version,version.index(name)+len(name),sum(payload)&0xffffffff)
    return bytes(version)


def build(project, size=None, target='u310', version_base=None):
    select_target(target)
    project=project.resolve()
    config=json.loads((project/'app.json').read_text())
    out=project/'build';out.mkdir(exist_ok=True)
    if 'text_asset' in config:text_asset(config['text_asset'],out)
    compiler=tool('clang','clang-18','clang-15')
    linker=tool('ld.lld','ld.lld-18','ld.lld-15')
    flags=['--target=arm-none-eabi','-mcpu=arm926ej-s','-mthumb','-Os','-ffreestanding','-fno-builtin',
           '-fno-pic','-fno-pie','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
           '-fno-stack-protector','-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror',*TARGETS[TARGET]['define'],
           '-I',str(SDK/'include'),'-I',str(out),'-I',str(project)]
    sources=[SDK/'runtime/runtime.c',SDK/'runtime/division.S']+[project/s for s in config['sources']]
    objects=[]
    for index,source in enumerate(sources):
        obj=out/f'{index}_{source.stem}.o'
        subprocess.run([compiler,*flags,'-c',str(source),'-o',str(obj)],check=True)
        objects.append(obj)
    elf=out/'app.elf'
    subprocess.run([linker,'-T',str(SDK/'runtime/pxo.ld'),'--emit-relocs','--gc-sections','--no-undefined',
                    '-Map='+str(out/'app.map'),'-o',str(elf),*map(str,objects)],check=True)
    report=pack(elf,out/'Calculator.pxo',size=size)
    if size is not None:
        (out/'Version').write_bytes(grown_version_file((out/'Calculator.pxo').read_bytes(),version_base))
    print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    new=sub.add_parser('new');new.add_argument('directory',type=Path)
    b=sub.add_parser('build');b.add_argument('project',type=Path)
    b.add_argument('--target',choices=sorted(TARGETS),default='u310',help='Firmware to build for (default u310)')
    b.add_argument('--version-base',type=Path,default=None,help='Version file to patch for grown builds (default: the original firmware one)')
    b.add_argument('--size',type=lambda v:int(v,0),default=None,
                    help='Grow the Calculator.pxo container to at least this many bytes (default: original ~41 KiB cap)')
    p=sub.add_parser('inspect');p.add_argument('payload',type=Path)
    setup=sub.add_parser('import-template',help='Import your original Calculator.pxo (not distributed)')
    setup.add_argument('payload',type=Path)
    setup.add_argument('--target',choices=sorted(TARGETS),required=True)
    setup.add_argument('--version',type=Path,help='Optional original Version file for larger apps')
    args=parser.parse_args()
    try:
        if args.command=='doctor':
            from elftools.elf.elffile import ELFFile
            from PIL import Image
            print('clang:',tool('clang','clang-18','clang-15'))
            print('linker:',tool('ld.lld','ld.lld-18','ld.lld-15'))
            for name,info in TARGETS.items():
                path=info['template']
                valid=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==info['sha']
                print(name+':', 'template ready' if valid else 'run import-template --target '+name)
            print('pyelftools, Pillow: available')
        elif args.command=='new':
            shutil.copytree(SDK/'examples/hello',args.directory,ignore=shutil.ignore_patterns('build','__pycache__'))
            print('Project created:',args.directory)
        elif args.command=='build':build(args.project,size=args.size,target=args.target,version_base=args.version_base)
        elif args.command=='import-template':
            info=TARGETS[args.target]
            data=args.payload.read_bytes()
            if hashlib.sha256(data).hexdigest()!=info['sha']:
                raise ValueError('Unsupported template: supply the original Calculator.pxo for '+args.target)
            version=args.version.read_bytes() if args.version else None
            info['template'].parent.mkdir(parents=True,exist_ok=True)
            info['template'].write_bytes(data)
            if version is not None:
                (info['template'].parent/'Version').write_bytes(version)
            print('Template imported for',args.target)
        elif args.command=='inspect':
            data=args.payload.read_bytes()
            if len(data)<0x104 or data[:4]!=b'PXO4':raise ValueError('Not a supported PXO4')
            print(json.dumps({'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'sum32':hex(sum(data)),
                              'relocations':struct.unpack_from('<I',data,0x10)[0],
                              'init':hex(struct.unpack_from('<I',data,struct.unpack_from('<I',data,12)[0]+24)[0]),
                              'entry':hex(struct.unpack_from('<I',data,struct.unpack_from('<I',data,12)[0]+28)[0])},indent=2))
    except (ValueError,OSError,ImportError,subprocess.CalledProcessError) as error:
        parser.exit(1,str(error)+'\n')
if __name__=='__main__':main()
