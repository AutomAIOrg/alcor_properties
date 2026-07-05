export interface CleaningType {
  cleaning_type_id: number;
  name: string;
  hourly_rate: number;
  active: boolean;
}

export interface CleaningTypeCreateRequest {
  name: string;
  hourly_rate: number;
  active: boolean;
}

export type CleaningTypeUpdateRequest = CleaningTypeCreateRequest;
