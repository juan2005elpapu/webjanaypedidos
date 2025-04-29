import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

def validate_image_format(image):
    """Valida que la imagen esté en un formato aceptable para conversión"""
    if not image or not hasattr(image, 'file') or not image.file:
        return
    try:
        image.file.seek(0)
        valid_formats = ['JPEG', 'PNG', 'GIF', 'BMP', 'TIFF', 'WebP']
        img = Image.open(image)
        if img.format not in valid_formats:
            raise ValidationError(
                f'Formato de imagen no soportado. Por favor usa: {", ".join(valid_formats)}'
            )
    except ValidationError:
        raise
    except Exception:
        # Si hay error al abrir la imagen, no validar (puede ser campo vacío)
        pass
    finally:
        try:
            image.file.seek(0)
        except Exception:
            pass

def convert_to_webp(image_field):
    """Convierte la imagen al formato WebP"""
    if not image_field or not hasattr(image_field, 'file') or not image_field.file:
        return None
    
    img_format = os.path.splitext(image_field.name)[1].lower()
    
    if img_format == '.webp':
        return None
    
    try:
        # Asegurarse de que el archivo está en la posición inicial
        image_field.file.seek(0)
        
        img = Image.open(image_field)
        
        # Convertir imagen a RGB si es necesario
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Crear un buffer para guardar la imagen convertida
        buffer = BytesIO()
        
        img.save(buffer, format='WEBP', quality=90, optimize=True)
        buffer.seek(0)
        
        new_name = os.path.splitext(os.path.basename(image_field.name))[0] + '.webp'
        
        return ContentFile(buffer.getvalue(), name=new_name)
    except Exception:
        # Si hay un error, dejamos la imagen original
        return None
    finally:
        # Asegurarse de que el archivo vuelve a la posición inicial
        if hasattr(image_field, 'file') and image_field.file:
            image_field.file.seek(0)
