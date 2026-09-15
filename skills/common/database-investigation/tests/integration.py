#!/usr/bin/env python3
"""Explicit destructive fixture setup ONLY in the task's disposable local containers.

Not discovered by run-tests.sh. Never point this harness at an existing database.
The collector itself performs no fixture setup and issues no application DDL/DML.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from core.registry import load_adapter
from core.connection import verify_probe
from core.live import collect
from core.output import write_reports


def setup(product, password):
    if product == "postgresql":
        import psycopg
        from psycopg import sql
        c = psycopg.connect(host="127.0.0.1", port=55439, dbname="investigation", user="postgres", password=password, autocommit=True)
        with c.cursor() as cur:
            cur.execute("CREATE SCHEMA app")
            cur.execute("CREATE TABLE app.parent (a INT,b INT,PRIMARY KEY(a,b))")
            cur.execute("CREATE TABLE app.child (a INT NOT NULL,b INT,CONSTRAINT fk FOREIGN KEY(a,b) REFERENCES app.parent(a,b))")
            cur.execute("CREATE INDEX child_ix ON app.child(a,b)")
            cur.execute("CREATE VIEW app.parent_view AS SELECT a,b FROM app.parent")
            cur.execute("INSERT INTO app.parent VALUES (1,2)")
            cur.execute("ANALYZE app.parent")
            cur.execute(sql.SQL("CREATE ROLE inv_reader LOGIN PASSWORD {}").format(sql.Literal(password)))
            cur.execute("GRANT USAGE ON SCHEMA app TO inv_reader")
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA app TO inv_reader")
        c.close()
        return dict(host="127.0.0.1",port=55439,database="investigation",user="inv_reader",password=password,plaintext=True), "app", "18.6"
    if product == "mysql":
        import pymysql
        c=pymysql.connect(host="127.0.0.1",port=53309,user="root",password=password,database="investigation",autocommit=True)
        with c.cursor() as cur:
            cur.execute("CREATE TABLE parent(a INT,b INT,PRIMARY KEY(a,b))")
            cur.execute("CREATE TABLE child(a INT NOT NULL,b INT,CONSTRAINT fk FOREIGN KEY(a,b) REFERENCES parent(a,b))")
            cur.execute("CREATE INDEX child_ix ON child(a,b)")
            cur.execute("CREATE VIEW parent_view AS SELECT a,b FROM parent")
            cur.execute("INSERT INTO parent VALUES (1,2)")
            cur.execute("CREATE USER 'inv_reader'@'%%' IDENTIFIED BY %s", (password,))
            cur.execute("GRANT SELECT, SHOW VIEW ON investigation.* TO 'inv_reader'@'%'")
        c.close()
        return dict(host="127.0.0.1",port=53309,database="investigation",user="inv_reader",password=password,plaintext=True), "investigation", "8.4.11"
    import oracledb
    c=oracledb.connect(host="127.0.0.1",port=51529,service_name="FREEPDB1",user="INVESTIGATOR",password=password)
    with c.cursor() as cur:
        cur.execute("CREATE TABLE parent(a NUMBER(10),b NUMBER(10),PRIMARY KEY(a,b))")
        cur.execute("CREATE TABLE child(a NUMBER(10) NOT NULL,b NUMBER(10),CONSTRAINT fk FOREIGN KEY(a,b) REFERENCES parent(a,b))")
        cur.execute("CREATE INDEX child_ix ON child(a,b)")
        cur.execute("CREATE VIEW parent_view AS SELECT a,b FROM parent")
        cur.execute("INSERT INTO parent VALUES (1,2)")
    c.commit()
    c.close()
    admin=oracledb.connect(host="127.0.0.1",port=51529,service_name="FREEPDB1",user="system",password=password)
    with admin.cursor() as cur:
        # Only a locally generated random test password; never logged.
        cur.execute('CREATE USER INV_READER IDENTIFIED BY "' + password.replace('"','""') + '"')
        cur.execute("GRANT CREATE SESSION TO INV_READER")
        for table in ("PARENT","CHILD","PARENT_VIEW"):
            cur.execute("GRANT SELECT ON INVESTIGATOR." + table + " TO INV_READER")
    admin.close()
    return dict(host="127.0.0.1",port=51529,service="FREEPDB1",user="INV_READER",password=password,plaintext=True), "INVESTIGATOR", "23.26"


def test(product, runtime, initialize):
    password=json.loads((runtime / "credentials.json").read_text())["password"]
    config_path=runtime/(product+"-config.json")
    if initialize:
        config,schema,version=setup(product,password)
        config_path.write_text(json.dumps(dict(config=config,schema=schema,version=version)))
        config_path.chmod(0o600)
    saved=json.loads(config_path.read_text())
    config,schema,version=saved["config"],saved["schema"],saved["version"]
    spec,module=load_adapter(product)
    port=module.connect(config)
    observed=verify_probe(spec,port,version,config.get("database"))
    now=lambda:datetime.now(timezone.utc).isoformat()
    started=now()
    result=collect(spec,port,schema,now,1000,120)
    print(product, observed["version"], [(c["id"],c["status"],c["row_count"]) for c in result["collections"]])
    bad=[c for c in result["collections"] if c["status"] not in {"ok","empty","disabled","not_collected"} and not (c["id"]=="index_reads" and c["status"]=="permission_denied")]
    if bad:
        raise AssertionError("query collection failed: " + ",".join(c["id"] for c in bad))
    tables=[o for o in result["objects"] if o["kind"]=="table"]
    assert {o["name"].lower() for o in tables}=={"parent","child"}, "table inventory includes unexpected objects"
    child=next(o for o in tables if o["name"].lower()=="child")
    assert [c["name"].lower() for c in child["columns"]]==["a","b"]
    fk=next(c for c in child["constraints"] if c["kind"]=="foreign_key")
    assert [x.lower() for x in fk["columns"]]==["a","b"]
    assert [x.lower() for x in fk["references"]["columns"]]==["a","b"]
    assert result["statistics"], "no statistics captured"
    assert password not in json.dumps(result,default=str)
    partial=any(c["status"] not in {"ok","empty"} for c in result["collections"])
    inv=dict(result,schema_version=1,run_id=now().replace(":","-"),mode="live",product=product,version=version,schema=schema,target_id="integration",status="partial" if partial else "complete",observed=observed,started_at=started,finished_at=now())
    dest=runtime/"reports"/product/inv["run_id"]
    write_reports(inv,dest,"en")
    import jsonschema
    jsonschema.validate(json.loads((dest/"inventory.json").read_text()),json.loads((ROOT/"inventory.schema.json").read_text()))
    # Also exercise the actual CLI via environment-only profile references.
    profile={"product":product,"expected_version":version,"schema":schema,"target_id":product,"allow_local_plaintext":True}
    for key,value in config.items():
        if key!="plaintext":
            env="NEXUS_INV_"+key.upper()
            os.environ[env]=str(value)
            profile[key+"_env"]=env
    profile_path=runtime/(product+"-profile.json")
    profile_path.write_text(json.dumps(profile))
    import subprocess
    cli=subprocess.run([sys.executable,str(ROOT/"scripts/investigate.py"),"live","--profile",str(profile_path),"--output-root",str(runtime/"cli-reports")],capture_output=True,text=True)
    assert cli.returncode in (0,2), "live CLI failed"
    assert password not in cli.stdout+cli.stderr
    print(product,"PASS: restricted user, composite FK, statistics, JSON Schema, live CLI")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("product",choices=["oracle","postgresql","mysql"])
    p.add_argument("--runtime",type=Path,required=True)
    p.add_argument("--initialize-disposable-fixtures",action="store_true")
    a=p.parse_args()
    test(a.product,a.runtime,a.initialize_disposable_fixtures)
