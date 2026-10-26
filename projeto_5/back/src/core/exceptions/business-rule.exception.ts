import { HttpException, HttpStatus } from '@nestjs/common';

export interface BusinessRule {
  code: string;
  message: string;
  status?: HttpStatus;
}

// Violation of a documented business rule (DEC-010): 412 by default, or the
// status the rule defines (e.g. 409 for uniqueness). The code goes to the
// client as business_rule_code.
export class BusinessRuleException extends HttpException {
  readonly businessRuleCode: string;

  constructor(rule: BusinessRule) {
    super(rule.message, rule.status ?? HttpStatus.PRECONDITION_FAILED);
    this.businessRuleCode = rule.code;
  }
}

// Each module declares its rules with this helper, so codes stay unique per catalog
// and the key is the code itself (no loose strings in services).
export function defineBusinessRules<K extends string>(
  rules: Record<K, Omit<BusinessRule, 'code'>>,
): Record<K, BusinessRule> {
  return Object.fromEntries(
    Object.entries<Omit<BusinessRule, 'code'>>(rules).map(([code, rule]) => [
      code,
      { ...rule, code },
    ]),
  ) as Record<K, BusinessRule>;
}
