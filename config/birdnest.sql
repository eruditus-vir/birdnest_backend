CREATE TABLE "drones" (
                          "serial_number" varchar PRIMARY KEY,
                          "manufacturer" varchar,
                          "mac" varchar,
                          "ipv4" varchar,
                          "ipv6" varchar,
                          "firmware" varchar,
                          "position_x" float8,
                          "position_y" float8,
                          "altitude" float8,
                          "snapshot_timestamp" datetime,
                          "is_violating_ndz" boolean,
                          "violated_pilot_id" int UNIQUE,
                          "created_at" datetime,
                          "update_at" datetime,
                          PRIMARY KEY ("serial_number")
);

CREATE TABLE "violated_pilots" (
                                   "pilot_id" varchar PRIMARY KEY,
                                   "first_name" varchar,
                                   "last_name" varchar,
                                   "phone_number" varchar,
                                   "email" varchar,
                                   "created_dt" timestamp,
                                   "last_violation_at" datetime,
                                   PRIMARY KEY ("pilot_id")
);

CREATE INDEX ON "drones" ("serial_number");

CREATE INDEX ON "drones" ("violated_pilot_id");

CREATE INDEX ON "drones" ("update_at");

CREATE INDEX ON "violated_pilots" ("pilot_id");

CREATE INDEX ON "violated_pilots" ("last_violation_at");

ALTER TABLE "violated_pilots" ADD FOREIGN KEY ("pilot_id") REFERENCES "drones" ("violated_pilot_id") ON DELETE CASCADE ON UPDATE NO ACTION;
