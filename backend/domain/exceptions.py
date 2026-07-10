"""
Excepciones de dominio para el backend de Alcor Properties.

Estas son excepciones puramente de negocio sin dependencia de frameworks HTTP.
La capa de API asigna cada excepción al código de estado HTTP apropiado.
"""


class DomainException(Exception):
    """Clase base para todas las excepciones de dominio."""

    pass


class BookingNotFound(DomainException):
    """Se lanza cuando no se puede encontrar una reserva por su identificador."""

    def __init__(self, record_id: int) -> None:
        self.record_id = record_id
        super().__init__(f"Reserva con ID {record_id} no encontrada")


class BookingConflict(DomainException):
    """Se lanza cuando una reserva se superpone con otra existente en las mismas fechas."""

    def __init__(self, check_in: str = "", check_out: str = "") -> None:
        detail = (
            f"Ya existe una reserva entre {check_in} y {check_out}"
            if check_in and check_out
            else "La reserva entra en conflicto con una reserva existente"
        )
        super().__init__(detail)


class DomainValidationError(DomainException):
    """Se lanza cuando se viola una regla de negocio (por ejemplo, check-out antes que check-in)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidToken(DomainException):
    """Se lanza cuando un token de acceso no es válido."""

    def __init__(self, message: str = "Token de acceso inválido") -> None:
        super().__init__(message)


class TokenExpired(DomainException):
    """Se lanza cuando un token de acceso ha expirado."""

    def __init__(self) -> None:
        super().__init__("Token de acceso expirado")


class InvalidCredentials(DomainException):
    """Se lanza cuando las credenciales de login no son válidas."""

    def __init__(self) -> None:
        super().__init__("Usuario o contraseña inválidos")


class UserAlreadyExists(DomainException):
    """Se lanza cuando un usuario ya existe."""

    def __init__(self, username: str) -> None:
        super().__init__(f"El usuario {username} ya existe")


class IntegrityError(DomainException):
    """Se lanza cuando ocurre un error de integridad."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class UserNotFound(DomainException):
    """Se lanza cuando un usuario no existe."""

    def __init__(self) -> None:
        super().__init__("Usuario no encontrado")


class UserDatabaseError(DomainException):
    """Se lanza cuando ocurre un error al interactuar con la base de datos de usuarios."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ApartmentAlreadyExistsError(DomainException):
    """Se lanza cuando un apartamento ya existe."""

    def __init__(self, apartment_id: str) -> None:
        super().__init__(f"El apartamento {apartment_id} ya existe")


class ApartmentDatabaseError(DomainException):
    """Se lanza cuando ocurre un error al interactuar con la base de datos de apartamentos."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ApartmentNotFoundError(DomainException):
    """Se lanza cuando un apartamento no existe."""

    def __init__(self, apartment_id: str) -> None:
        super().__init__(f"El apartamento {apartment_id} no existe")


class ApartmentHasBookingsError(DomainException):
    """Se lanza cuando un apartamento tiene reservas."""

    def __init__(self, apartment_id: str) -> None:
        super().__init__(
            f"El apartamento {apartment_id} no puede ser eliminado porque tiene reservas"
        )


class BillNotFoundError(DomainException):
    """Se lanza cuando no se puede encontrar una factura por su identificador."""

    def __init__(self, bill_id: int) -> None:
        self.bill_id = bill_id
        super().__init__(f"Factura con ID {bill_id} no encontrada")


class BillAlreadyExistsError(DomainException):
    """Se lanza cuando ya existe una factura para la reserva (limpieza) indicada."""

    def __init__(self, record_id: int) -> None:
        self.record_id = record_id
        super().__init__(f"Ya existe una factura para la reserva {record_id}")


class CleaningTypeNotFoundError(DomainException):
    """Se lanza cuando no se puede encontrar un tipo de limpieza por su identificador."""

    def __init__(self, cleaning_type_id: int) -> None:
        self.cleaning_type_id = cleaning_type_id
        super().__init__(f"Tipo de limpieza con ID {cleaning_type_id} no encontrado")


class CleaningTypeAlreadyExistsError(DomainException):
    """Se lanza cuando ya existe un tipo de limpieza con el mismo nombre."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"El tipo de limpieza '{name}' ya existe")


class BillDocumentRenderError(DomainException):
    """Se lanza cuando falla la generación del documento PDF de factura."""

    def __init__(self, message: str = "No se pudo generar el documento de factura") -> None:
        super().__init__(message)


class BillDocumentAlreadyExistsError(DomainException):
    """Se lanza cuando ya existe un documento de factura para la factura indicada."""

    def __init__(self, bill_id: int) -> None:
        self.bill_id = bill_id
        super().__init__(f"Ya existe un documento de factura para la factura {bill_id}")


class BillDocumentNotFoundError(DomainException):
    """Se lanza cuando no se encuentra un documento de factura."""

    def __init__(self, bill_id: int) -> None:
        self.bill_id = bill_id
        super().__init__(f"No se encontró documento de factura para la factura {bill_id}")


class BillDocumentNotUpdatedError(DomainException):
    """Se lanza cuando no se puede actualizar un documento de factura."""

    def __init__(self, bill_id: int) -> None:
        self.bill_id = bill_id
        super().__init__(f"No se pudo actualizar el documento de factura para la factura {bill_id}")


class FileStorageError(DomainException):
    """Se lanza cuando falla la subida de un archivo al almacenamiento remoto (NAS)."""

    def __init__(self, message: str = "No se pudo almacenar el archivo en el NAS") -> None:
        super().__init__(message)
