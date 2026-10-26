import { ValueTransformer } from 'typeorm';

// JSON stored in nvarchar(max): SQL Server has no JSON column type in 2022.
export const jsonTransformer: ValueTransformer = {
  to: (value: unknown) =>
    value === undefined || value === null ? value : JSON.stringify(value),
  from: (value: unknown) =>
    typeof value === 'string' ? (JSON.parse(value) as unknown) : value,
};
