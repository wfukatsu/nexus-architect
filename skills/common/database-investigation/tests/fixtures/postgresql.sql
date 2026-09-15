CREATE TABLE app.parent (a INTEGER, b INTEGER, PRIMARY KEY (a,b));
CREATE TABLE app.child (a INTEGER NOT NULL, b INTEGER,
  CONSTRAINT fk FOREIGN KEY (a,b) REFERENCES app.parent(a,b));
CREATE INDEX child_ix ON app.child(a,b);
