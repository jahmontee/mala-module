# SPDX-License-Identifier: MIT
"""Exact optional component states and the public Mala beta6 upgrade."""
import json
from pathlib import Path
from transaction import canonical,digest,file_hash,safe
COMPONENTS=('mala','network-link','squelch-box')
LEGACY_SUFFIX='~mala-beta6'
def name(modules):return '+'.join(sorted(modules)) or 'stock407'
def state_name(modules,legacy=False):
    return name(modules)+(LEGACY_SUFFIX if legacy and 'mala' in modules else '')
def load(path):
    value=json.loads(Path(path).read_text())
    if value.get('schema')!='hector-community/catalog/2' or set(value.get('components',{}))!=set(COMPONENTS):raise ValueError('Unsupported component catalog')
    if len(value['states'])!=12:raise ValueError('Incomplete compatibility matrix')
    paths=set(value['paths'])
    for key,state in value['states'].items():
        legacy=state.get('mala_version')=='0.1.0-beta.6'
        if key!=state_name(state['components'],legacy) or set(state['files'])!=paths or set(state['components'])-set(COMPONENTS):raise ValueError('Invalid component state')
    return value

def detect(root,catalog):
    observed={p:file_hash(safe(root,p)) for p in catalog['paths']}
    found=[k for k,v in catalog['states'].items() if v['files']==observed]
    if len(found)!=1:raise ValueError('Unsupported or modified component files. No files have been overwritten.')
    for p,h in catalog['guards'].items():
        if file_hash(safe(root,p))!=h:raise ValueError('Firmware guard differs: '+p)
    return found[0]

def component_versions(catalog,state):
    row=catalog['states'][state]
    result={key:dict(catalog['components'][key]) for key in row['components']}
    if 'mala' in result:result['mala']['version']=row['mala_version']
    return result

def migration(catalog,old_digest):
    if old_digest==digest(canonical(catalog)):return None
    accepted=catalog.get('legacy_catalogs',{}).get(old_digest)
    if accepted is None:raise ValueError('A reviewed catalog migration is required')
    return accepted

def translate_state(catalog,old_digest,state):
    accepted=migration(catalog,old_digest)
    if accepted is None:
        if state not in catalog['states']:raise ValueError('Unknown inventory state')
        return state
    if state not in accepted['states']:raise ValueError('Unknown legacy inventory state')
    return accepted['states'][state]

def transition(catalog,current,component,action):
    if component not in COMPONENTS or action not in ('install','rollback'):raise ValueError('Unknown component/action')
    before=catalog['states'][current];modules=set(before['components'])
    upgrading=component=='mala' and action=='install' and current.endswith(LEGACY_SUFFIX)
    if (component in modules)==(action=='install') and not upgrading:return None
    if action=='install':modules.add(component)
    else:modules.remove(component)
    target=state_name(modules,current.endswith(LEGACY_SUFFIX) and component!='mala');after=catalog['states'][target]
    rows=[];guards=dict(catalog['guards'])
    for p in catalog['paths']:
        old,new=before['files'][p],after['files'][p]
        if old==new:guards[p]=old;continue
        meta=catalog['artifacts'].get(new,{})
        rows.append(dict(path=p,before_sha256=old,sha256=new,size=meta.get('size',0),mode=meta.get('mode',0o644)))
    if not rows:raise ValueError('Empty component transition')
    return dict(schema='hector-community/transition/1',version=catalog['components'][component]['version'],component=component,action=action,from_state=current,to_state=target,catalog_sha256=digest(canonical(catalog)),hardware='Hector',firmware='407',architecture='aarch64',files=rows,file_count=len(rows),guards=guards,require_absent=[])

def values(folder,manifest):
    result={}
    for row in manifest['files']:
        if row['sha256'] is None:continue
        raw=safe(Path(folder)/'blobs',row['sha256']).read_bytes()
        if digest(raw)!=row['sha256'] or len(raw)!=row['size']:raise ValueError('Missing or corrupt kit file: '+row['path'])
        result[row['path']]=raw
    return result
