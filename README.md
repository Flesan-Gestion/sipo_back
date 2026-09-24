# Documentación

# ¿Cómo usar en tu proyecto?

1. Clona este repositorio

```
git clone https://github.com/Flesan-Gestion/template_django.git
```

2. Agrega el repositorio remoto de tu proyecto

```
git remote add origin-myproject https://github.com/Flesan-Gestion/template_django.git
```

3. Verifica que se haya guardado el repositorio remoto

```
git remote -v
```

4. Verás un listado como este donde debería figurar tu repositorio

```
> origin  https://github.com/Flesan-Gestion/template_django.git (fetch)
> origin  https://github.com/Flesan-Gestion/template_django.git (push)
> origin-myproject  https://github.com/Flesan-Gestion/myproject.git (fetch)
> origin-myproject  https://github.com/Flesan-Gestion/myproject.git (push)
```

5. Empuja la rama main a tu repositorio remoto

```
git push -u origin-myproject main
```

6. El template ya se encuentra en tu repositorio remoto. Ahora clona tu proyecto y trabaja sobre él.

```
git clone https://github.com/Flesan-Gestion/template_django.git
```


# Configuración Inicial del Proyecto

1. Generación del entorno virtual

```
py -m venv venv
```

2. Activar el entorno virtual

```
.\venv\Scripts\activate
```

3. Utilizamos la versión 4 de Django debido a que es la versión compatible con la versión de postgresql del datawarehouse. Todas las dependencias están en el archivo `requirements.txt`. Usa el siguiente comando para instalar todas esas dependencias.

```
py -m pip install -r .\requirements.txt
```

4. Crear archivo `cache.json` con un objeto vacío en la raíz del proyecto.

4. Variables de entorno. Armarás tu .env con esta estructura.

```
# Host donde se desplegará la API
HOST=localhost:5173
# Puerto donde se desplegará la API
PORT=8000

# Host de la web frontend que consume la api
WEB_HOST=http://localhost:5173
WEB_URL=http://localhost:5173

# Motor de base de datos a usar
DB_ENGINE=django.db.backends.postgresql

# Variables
[LOCALHOST]
ID_APP=29 # Id de aplicación
ROL_PERFIL01=1 # Roles del aplicativo
ROL_PERFIL02=2

# Host y puerto del servidor
DB_HOST=localhost
DB_PORT=5432

# Credenciales de la base de datos principal del proyecto
DB_DATABASE_APP=postgres
DB_USERNAME_APP=user
DB_PASSWORD_APP=password
DB_SCHEMA_APP="app_schema"

# Credenciales de la base de datos de seguridad app de postgres
DB_DATABASE_SECURITY=postgres
DB_USERNAME_SECURITY=user
DB_PASSWORD_SECURITY=password
DB_SCHEMA_SECURITY="app_seguridad_app"

# Clave secreta del JWT
JWT_SECRET_KEY=C9Nf4ZSovUgr9qQMwmvGSREZ4HexmH7aFTbowy8UcHKnMKQ9Fj

# Credenciales de la API Flesan. Necesarias para el uso del servicio de envío de mails.
API_GF_USERNAME=username
API_GF_PASSWORD=password
API_GF_URL="https://api.grupoflesan.com/api"

# Enlaces a la API de Google para validar Tokens
GOOGLE_USER_INFO_URL="https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKEN_INFO_URL="https://oauth2.googleapis.com/tokeninfo?access_token="

# Google Client Id de la Consola de Google Cloud
GOOGLE_CLIENT_ID="..."
```

# Contenido de las apps principales

### Utilitarios (utils)

1. `json_cache.py`: Esta clase está configurada en el settings del proyecto para ser la encargada del manejo del caché. Para esto es que creamos anteriormente el archivo `cache.json`.

2. `middleware.py`: Contiene dos middleware para manejo de excepciones. Uno mapea errores a nivel de API y otro mapea errores a nivel general de Django.

3. `repository.py`: Contiene una clase llamada **EssentialRepository** de la cual heredarán los repositorios de cada modelo en específico y contiene operaciones básicas para hacer con los modelos. Este **EssentialRepository** tiene tres propiedades:
    - `self.model`: Modelo sobre el cual se harán las operaciones.
    - `self.logical_deletion`: Especifica si el modelo tiene eliminación lógica, es decir, tiene el campo de enable.
    - `self.connection`: Refiere a la conexión de base de datos que se usará para realizar las operaciones. Por defecto usa la conexión `default` que vendría siendo la conexión a la base de datos principal de tu proyecto.

4. `responses.py`: Contiene clases para formatear las respuestas JSON de las vistas:

    - `ApiResponseSuccess`: Recibe como parámetro cualquier cosa o una instancia de clase `Data`. Usualmente usarías instancias de clase Data cuando quieras mostrar un listado puesto que este puede guardar información de paginación, conteo de items, etc. En la vista de usuario hay ejemplo de esto.
    - `ApiResponseError`: Formateo igual al del success pero en caso de errores. Ya se encuentra configurado para el manejo de excepciones en los middlewares y validaciones de tokens.
    - `Data`: La clase que mencionaba que usarán mas en casos de listados.

5. `serializers.py`: Contiene los serializadores de los ApiResponses (no los usarán, solo sirve para el archivo de repsonses). También tiene el `EssentialSerializer`. Este es el serializer que usarán para crear otros serializer. Es decir, cuando crees un serializer heredará del `EssentialSerializer`.
    - El `EssentialSerializer` permite especificar los campos del modelo que deseas mostrar colocando `fields=["campo1", "campo2"]` en los parámetros al momento de usarlo.
    - El `EssentialSerializer` permite especificar las relaciones del modelo que deseas mostrar colocando `relations=["relacion1", "relacion2"]` en los parámetros al momento de usarlo.

6. `services.py`: Contiene servicios de uso externo. En este caso el envío de correos.

### Seguridad (security)

1. `authentication.py`: Autenticación JWT encargada de validar el token y extraer el usuario de dicho token.

2. `repositories/auth_repository.py`: En este repositorio hay 3 métodos para generar 3 tipos de tokens.
    - `generateToken(user:User)`: Token común que contiene la información del usuario.
    - `generateCustomToken(properties)`: Token no válido para hacer consultas. No contiene información de usuario, solo es para transmitir información de un lugar a otro de forma encriptada en los claims.
    - `generateScopedToken(routes)`: Tokens válidos que recibe las rutas o endpoints a los que tiene acceso. Este token solo es válido una vez. Una vez usado se guarda en la blacklist.

> Nota: Las rutas por defecto tienen una especie de **alias**. Esta está conformada por el basename de la ruta de la vista y el nombre del método. Por ejemplo, el alias del endpoint de getById de la vista UserView sería `user-getById`. Usando el método `reverse` de `django.urls` puedes obtener la ruta a la que hace referencia ese alias. 

2. `decorators.py`: Decoradores para validar accesos a endpoints en específico:
    - `role_required()`: Valida los roles del usuario pasados por parámetro en el arreglo. Así limitamos los accesos en base al usuario.
    - `scoped_token()`: Valida los tokens de tipo scoped. Colocar siempre antes del `role_required()` cuando se use.

3. `permissions.py`: Contiene la clase de autenticación encargada de validar los permisos `TokenAuth`.

4. `token_blacklist.py`: Clase para agregar tokens a la blacklist y verificar si un token ya se encuentra en él. Realmente usa la propia memoria caché para estas validaciones.

# ¿Cómo estructurar normalmente las apps?

- `repositories`: Repositorios por cada modelo. Inicializar heredando el `EssentialRepository` para tener todas las operaciones base en caso de ser necesario.

- `views`: Vistas por cada modelo. Está el ejemplo del UserView donde también hay una muestra de su uso con paginación.

- `models.py`: Trabaja los modelos relacionados a tu app en este archivo como normalmente lo hace django.

- `urls.py`: Rutas de las vistas del app. Luego estas se agregarán en la configuración de rutas del proyecto en general.

# InspectDB - Convertir tablas a modelos
- InspectDB es una extensión que ya viene con django que permite transformar las tablas de una base de datos a modelos de python. Para ello usamos este comando
```
py manage.py inspectdb --database [database_connection] > models.py 
```
- Esto generará un archivo `models.py` en la raíz de tu proyecto con los modelos que pudo extraer de las tablas de la conexión a base de datos que especificaste.