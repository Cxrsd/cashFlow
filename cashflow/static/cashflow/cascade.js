// каскад тип -> категория -> подкатегория в форме операции,
// селекты только сужают выбор, сохраняется одна подкатегория
document.addEventListener("DOMContentLoaded", function () {
    var typeSelect = document.getElementById("id_transaction_type");
    var categorySelect = document.getElementById("id_category");
    var subcategorySelect = document.getElementById("id_subcategory");
    if (!typeSelect || !categorySelect || !subcategorySelect) {
        return;
    }

    function filterOptions(select, attr, parentId) {
        Array.prototype.forEach.call(select.options, function (option) {
            if (!option.value) {
                return; // пустой пункт оставляем всегда
            }
            var visible = Boolean(parentId) && option.dataset[attr] === parentId;
            option.hidden = !visible;
            option.disabled = !visible; // hidden внутри select работает не везде
            if (!visible && option.selected) {
                select.value = "";
            }
        });
    }

    function applyCategory() {
        filterOptions(subcategorySelect, "category", categorySelect.value);
    }

    function applyType() {
        filterOptions(categorySelect, "type", typeSelect.value);
        applyCategory();
    }

    typeSelect.addEventListener("change", applyType);
    categorySelect.addEventListener("change", applyCategory);
    applyType();
});
