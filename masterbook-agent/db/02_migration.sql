ALTER TABLE followup_current ADD COLUMN actor TEXT NULL;
ALTER TABLE followup_current ADD COLUMN source TEXT NULL;
ALTER TABLE followup_history ADD COLUMN actor TEXT NULL;
ALTER TABLE followup_history ADD COLUMN source TEXT NULL;
UPDATE followup_current SET actor='legacy', source='web' WHERE source IS NULL;
UPDATE followup_history SET actor='legacy', source='web' WHERE source IS NULL;

CREATE TRIGGER trg_fc_ai AFTER INSERT ON followup_current
BEGIN
  INSERT INTO followup_history (current_id,outlet_id,sales_owner,status,note,next_followup,
    version,changed_at,actor,source)
  VALUES (NEW.id,NEW.outlet_id,NEW.sales_owner,NEW.status,NEW.note,NEW.next_followup,
    NEW.version,NEW.updated_at,NEW.actor,NEW.source);
END;

CREATE TRIGGER trg_fc_au AFTER UPDATE ON followup_current
BEGIN
  INSERT INTO followup_history (current_id,outlet_id,sales_owner,status,note,next_followup,
    version,changed_at,actor,source)
  VALUES (NEW.id,NEW.outlet_id,NEW.sales_owner,NEW.status,NEW.note,NEW.next_followup,
    NEW.version,NEW.updated_at,NEW.actor,NEW.source);
END;