CREATE TABLE investigation.parent (a INT, b INT, PRIMARY KEY (a,b));
CREATE TABLE investigation.child (a INT NOT NULL, b INT,
  CONSTRAINT fk FOREIGN KEY (a,b) REFERENCES investigation.parent(a,b));
CREATE INDEX child_ix ON investigation.child(a,b);
