from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.security import get_current_user
from app.db.session import get_db_connection
from app.schemas.stats import MAX_YEAR, MIN_YEAR, GoalIn, GoalOut

router = APIRouter(prefix="/goals", tags=["Metas de lectura"])

YearPath = Path(..., ge=MIN_YEAR, le=MAX_YEAR, description="Año calendario de la meta")


@router.get("/{year}", response_model=GoalOut, summary="Obtener la meta anual de lectura")
def get_goal(year: int = YearPath, current_user_id: int = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT target_books FROM reading_goals WHERE user_id = :user_id AND goal_year = :goal_year",
            {"user_id": current_user_id, "goal_year": year},
        )
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No hay meta para ese año")
    return GoalOut(year=year, target_books=row[0])


@router.put("/{year}", response_model=GoalOut, summary="Crear o actualizar la meta anual de lectura")
def upsert_goal(body: GoalIn, year: int = YearPath, current_user_id: int = Depends(get_current_user)):
    # SELECT + UPDATE/INSERT en vez de MERGE (evita ORA-12860 en Oracle ADB).
    with get_db_connection() as conn:
        cursor = conn.cursor()
        params = {"user_id": current_user_id, "goal_year": year, "target_books": body.target_books}
        cursor.execute(
            "UPDATE reading_goals SET target_books = :target_books, updated_at = SYSTIMESTAMP "
            "WHERE user_id = :user_id AND goal_year = :goal_year",
            params,
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO reading_goals (user_id, goal_year, target_books) "
                "VALUES (:user_id, :goal_year, :target_books)",
                params,
            )
    return GoalOut(year=year, target_books=body.target_books)


@router.delete("/{year}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar la meta anual")
def delete_goal(year: int = YearPath, current_user_id: int = Depends(get_current_user)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM reading_goals WHERE user_id = :user_id AND goal_year = :goal_year",
            {"user_id": current_user_id, "goal_year": year},
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="No hay meta para ese año")
