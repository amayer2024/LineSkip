-- 004: valid_date is now enforced at purchase (expired passes are rejected). Bump any
-- pass products still carrying an old seed date into the future, so data seeded before the
-- rule stays buyable. Data-preserving: only valid_date changes, and only on stale rows.
UPDATE dbo.pass_products
   SET valid_date = '2027-12-31'
 WHERE valid_date < '2027-01-01';
GO
