import pytest
from app.utils.pagination import Pagination


#plain class so don't need app context - hurray
def test_basic_pagination():
    items = list(range(10))
    pag = Pagination(items=items, page=1, per_page=5, total=10)
    assert pag.page == 1
    assert pag.per_page == 5
    assert pag.total == 10
    assert pag.pages == 2
    assert pag.has_prev is False
    assert pag.has_next is True
    assert pag.prev_num is None
    assert pag.next_num == 2

def test_iter_pages():
    pag = Pagination(items=[], page=3, per_page=1, total=5)
    pages = list(pag.iter_pages())
    assert 3 in pages
    assert pages[0] == 1
    assert pages[-1] == 5

def test_iter_pages_with_gaps():
    pag = Pagination(items=[], page=5, per_page=1, total=10)
    pages = list(pag.iter_pages(left_edge=1, left_current=1, right_current=1, right_edge=1))
    # There should be None values representing gaps
    assert None in pages
    # The first and last pages should always be present
    assert 1 in pages
    assert 10 in pages

#Edge cases:
def test_pagination_less_than_one_page():
    items = list(range(3))
    pag = Pagination(items=items, page=1, per_page=10, total=3)
    assert pag.pages == 1
    assert pag.has_prev is False
    assert pag.has_next is False
    assert pag.prev_num is None
    assert pag.next_num is None
    pages = list(pag.iter_pages())
    assert pages == [1]

def test_pagination_large_number_of_items():
    items = list(range(999))
    pag = Pagination(items=items, page=50, per_page=10, total=999)
    assert pag.pages == 100
    assert pag.has_prev is True
    assert pag.has_next is True
    assert pag.prev_num == 49
    assert pag.next_num == 51
    pages = list(pag.iter_pages(left_edge=2, left_current=2, right_current=2, right_edge=2))
    assert 1 in pages
    assert 100 in pages
    assert 50 in pages
    assert None in pages  