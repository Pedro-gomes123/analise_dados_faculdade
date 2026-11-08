import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';

// Routes open without login (PER-001, PER-013). Every other route requires a token.
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
