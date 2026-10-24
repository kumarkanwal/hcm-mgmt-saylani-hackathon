from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SetupRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=150)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)

    @field_validator("company_name")
    @classmethod
    def trim_company_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Company name must not be blank")
        return cleaned

    @field_validator("admin_email", mode="before")
    @classmethod
    def normalize_admin_email(cls, value: object) -> object:
        return str(value).strip().lower() if isinstance(value, str) else value

    @field_validator("admin_password")
    @classmethod
    def validate_bcrypt_limit(cls, value: str) -> str:
        try:
            encoded_length = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("Password contains invalid characters") from exc
        if encoded_length > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class SetupStatusResponse(BaseModel):
    is_setup_done: bool


class SetupResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return str(value).strip().lower() if isinstance(value, str) else value


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_bcrypt_limit(cls, value: str) -> str:
        try:
            encoded_length = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("Password contains invalid characters") from exc
        if encoded_length > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    department: str | None = None
    designation: str | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    employee_id: int | None
    must_change_password: bool
    employee: EmployeeSummary | None = None


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse
