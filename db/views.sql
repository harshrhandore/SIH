CREATE MATERIALIZED VIEW mv_admissions AS
SELECT s.institution_id,s.program_id,s.admission_year AS year,count(*)::integer AS admitted
FROM students s
WHERE s.program_id IS NOT NULL AND s.admission_year IS NOT NULL
GROUP BY s.institution_id,s.program_id,s.admission_year;
CREATE UNIQUE INDEX ux_mv_admissions ON mv_admissions(institution_id,program_id,year);

CREATE MATERIALIZED VIEW mv_placements AS
WITH eligible AS (
 SELECT s.id,s.institution_id,s.program_id,
        (s.admission_year+p.duration_years)::smallint AS year
 FROM students s JOIN programs p ON p.id=s.program_id
 WHERE s.current_year=p.duration_years AND s.status<>'WITHDRAWN' AND s.admission_year IS NOT NULL
), best_offer AS (
 SELECT e.id,e.institution_id,e.program_id,e.year,
        max(pl.package_lpa) FILTER (WHERE pl.offer_status IN ('OFFERED','ACCEPTED')) AS package
 FROM eligible e LEFT JOIN placements pl ON pl.student_id=e.id AND pl.placement_year=e.year
 GROUP BY e.id,e.institution_id,e.program_id,e.year
)
SELECT institution_id,program_id,year,count(*)::integer AS eligible_students,
 count(package)::integer AS placed_students,
 round(100.0*count(package)/nullif(count(*),0),2) AS placement_rate,
 percentile_cont(0.5) WITHIN GROUP (ORDER BY package) FILTER (WHERE package IS NOT NULL) AS median_package_lpa,
 max(package) AS max_package_lpa
FROM best_offer GROUP BY institution_id,program_id,year;
CREATE UNIQUE INDEX ux_mv_placements ON mv_placements(institution_id,program_id,year);

CREATE MATERIALIZED VIEW mv_performance AS
WITH yearly AS (
 SELECT ap.student_id,ap.academic_year AS year,
   bool_and(ap.sgpa>=4) AS passed_all_terms,
   (array_agg(ap.cgpa ORDER BY ap.term_no DESC))[1] AS latest_cgpa
 FROM academic_performance ap GROUP BY ap.student_id,ap.academic_year
)
SELECT s.institution_id,s.program_id,p.branch,y.year,count(*)::integer AS assessed_students,
 round(avg(y.latest_cgpa),2) AS avg_cgpa,
 round(100.0*count(*) FILTER (WHERE y.passed_all_terms)/nullif(count(*),0),2) AS pass_percent,
 count(*) FILTER (WHERE y.latest_cgpa<4)::integer AS bucket_0_4,
 count(*) FILTER (WHERE y.latest_cgpa>=4 AND y.latest_cgpa<6)::integer AS bucket_4_6,
 count(*) FILTER (WHERE y.latest_cgpa>=6 AND y.latest_cgpa<8)::integer AS bucket_6_8,
 count(*) FILTER (WHERE y.latest_cgpa>=8)::integer AS bucket_8_10
FROM yearly y JOIN students s ON s.id=y.student_id JOIN programs p ON p.id=s.program_id
GROUP BY s.institution_id,s.program_id,p.branch,y.year;
CREATE UNIQUE INDEX ux_mv_performance ON mv_performance(institution_id,program_id,branch,year);

CREATE MATERIALIZED VIEW mv_data_quality AS
SELECT i.id AS institution_id,i.expected_records,count(s.id)::integer AS total,
 count(s.id) FILTER (WHERE s.data_quality_status='PASSED_LOCAL_CHECKS')::integer AS clean,
 count(s.id) FILTER (WHERE s.data_quality_status='FLAGGED_FOR_REVIEW')::integer AS flagged,
 count(s.id) FILTER (WHERE s.data_quality_status='INCOMPLETE')::integer AS incomplete,
 count(s.id) FILTER (WHERE s.external_status='EXTERNAL_VERIFICATION_PENDING')::integer AS external_pending,
 least(100.0,round(100.0*count(s.id)/i.expected_records,2)) AS submission_percent,
 greatest(0,i.expected_records-count(s.id))::integer AS missing_records,
 (SELECT count(*)::integer FROM review_cases rc JOIN students rs ON rs.id=rc.student_id
   WHERE rs.institution_id=i.id AND rc.status<>'APPROVED') AS pending_reviews
FROM institutions i LEFT JOIN students s ON s.institution_id=i.id
GROUP BY i.id,i.expected_records;
CREATE UNIQUE INDEX ux_mv_quality ON mv_data_quality(institution_id);

INSERT INTO analytics_refresh_state(view_name,status)
VALUES ('mv_admissions','NEVER'),('mv_placements','NEVER'),('mv_performance','NEVER'),('mv_data_quality','NEVER');

ALTER TABLE analytics_refresh_state ADD COLUMN source_epoch bigint NOT NULL DEFAULT 0;
CREATE FUNCTION refresh_demo_views() RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE v_epoch bigint; v_stamp timestamptz;
BEGIN
 IF NOT pg_try_advisory_xact_lock(26263,4) THEN RETURN false; END IF;
 SELECT COALESCE(sum(data_epoch),0) INTO v_epoch FROM institution_epochs;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_admissions;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_placements;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_performance;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_data_quality;
 v_stamp:=clock_timestamp();
 UPDATE analytics_refresh_state SET status='READY',refreshed_at=v_stamp,source_epoch=v_epoch,error=NULL;
 INSERT INTO data_quality_snapshots(institution_id,snapshot_date,total,clean,flagged,incomplete)
 SELECT institution_id,(v_stamp AT TIME ZONE 'Asia/Kolkata')::date,total,clean,flagged,incomplete
 FROM mv_data_quality
 ON CONFLICT(institution_id,snapshot_date) DO UPDATE
 SET total=EXCLUDED.total,clean=EXCLUDED.clean,flagged=EXCLUDED.flagged,incomplete=EXCLUDED.incomplete;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION refresh_demo_views() FROM PUBLIC;
