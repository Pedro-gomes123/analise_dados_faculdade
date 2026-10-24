import { plainToInstance, Transform } from 'class-transformer';
import {
  IsBoolean,
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  Max,
  Min,
  MinLength,
  validateSync,
} from 'class-validator';

export enum NodeEnv {
  Development = 'development',
  Test = 'test',
  Production = 'production',
}

// Reads the raw value: enableImplicitConversion would turn 'false' into true.
const toBoolean = ({
  obj,
  key,
}: {
  obj: Record<string, unknown>;
  key: string;
}) =>
  obj[key] === undefined ? undefined : obj[key] === true || obj[key] === 'true';

export class EnvironmentVariables {
  @IsEnum(NodeEnv)
  NODE_ENV: NodeEnv = NodeEnv.Development;

  @IsInt()
  @Min(1)
  @Max(65535)
  PORT: number = 3000;

  @IsString()
  @IsNotEmpty()
  DB_HOST!: string;

  @IsInt()
  @Min(1)
  @Max(65535)
  DB_PORT: number = 1433;

  @IsString()
  @IsNotEmpty()
  DB_USER!: string;

  @IsString()
  @IsNotEmpty()
  DB_PASSWORD!: string;

  @IsString()
  @IsNotEmpty()
  DB_NAME!: string;

  @Transform(toBoolean)
  @IsBoolean()
  DB_ENCRYPT: boolean = true;

  @Transform(toBoolean)
  @IsBoolean()
  DB_TRUST_SERVER_CERTIFICATE: boolean = false;

  // DEC-013. At least 32 characters so a weak secret never reaches production.
  @IsString()
  @MinLength(32)
  JWT_SECRET!: string;

  // Format accepted by jsonwebtoken: number + s/m/h/d (e.g. 8h).
  @Matches(/^\d+[smhd]$/)
  JWT_EXPIRES_IN: `${number}${'s' | 'm' | 'h' | 'd'}` = '8h';
}

export function validateEnv(config: Record<string, unknown>) {
  const validated = plainToInstance(EnvironmentVariables, config, {
    enableImplicitConversion: true,
    exposeDefaultValues: true,
  });
  const errors = validateSync(validated, { skipMissingProperties: false });

  if (errors.length > 0) {
    const messages = errors.flatMap((error) =>
      Object.values(error.constraints ?? {}),
    );
    throw new Error(`Invalid environment variables:\n${messages.join('\n')}`);
  }

  return validated;
}
