from pathlib import Path
import os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
fixture=ROOT/'sqlite_export.json'
if not (ROOT/'db.sqlite3').exists():
    raise SystemExit('db.sqlite3 não encontrado. Coloque o banco antigo na raiz do projeto.')
env=os.environ.copy();env['USE_SQLITE']='1'
print('1/5 Atualizando estrutura do SQLite antigo...')
subprocess.check_call([PY,'manage.py','makemigrations','core'],cwd=ROOT,env=env)
subprocess.check_call([PY,'manage.py','migrate'],cwd=ROOT,env=env)
print('2/5 Exportando SQLite...')
r=subprocess.run([PY,'manage.py','dumpdata','--natural-foreign','--natural-primary','--exclude','contenttypes','--exclude','auth.permission','--indent','2'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if r.returncode:
    sys.stderr.buffer.write(r.stderr);raise SystemExit(r.returncode)
fixture.write_bytes(r.stdout)
env=os.environ.copy();env['USE_SQLITE']='0'
print('3/5 Criando estrutura no PostgreSQL...')
subprocess.check_call([PY,'manage.py','migrate'],cwd=ROOT,env=env)
print('4/5 Importando dados...')
subprocess.check_call([PY,'manage.py','loaddata',str(fixture)],cwd=ROOT,env=env)
print('5/5 Conferindo sistema...')
subprocess.check_call([PY,'manage.py','check'],cwd=ROOT,env=env)
print('Migração concluída. Guarde o db.sqlite3 como backup por alguns dias.')
