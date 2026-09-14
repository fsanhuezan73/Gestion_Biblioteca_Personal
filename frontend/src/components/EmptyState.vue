<template>
  <div class="card border-0 text-center py-5 px-3 my-4 empty-state">
    <div class="empty-state-icon">📚</div>
    <p class="page-kicker mt-3 mb-1">Tu espacio de lectura</p>
    <h3 class="display-font fw-bold">Tu biblioteca está vacía</h3>
    <p class="text-muted mb-4">Empieza añadiendo tu primer libro para construir tu colección.</p>
    <RouterLink to="/books/add" class="btn btn-primary btn-lg">
      + Añadir tu primer libro
    </RouterLink>
  </div>
</template>

<style scoped>
.empty-state {
  background: linear-gradient(135deg, #fff 0%, #f1f4ff 100%);
}
.empty-state-icon {
  font-size: 4rem;
}
</style>
