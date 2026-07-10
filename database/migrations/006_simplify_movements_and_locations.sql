-- Migration 006: simplify movement/location schema
-- Removes the low-value columns that are no longer part of the active model.

ALTER TABLE public.movements
    DROP COLUMN IF EXISTS concepts;

ALTER TABLE public.locations
    DROP COLUMN IF EXISTS country;
