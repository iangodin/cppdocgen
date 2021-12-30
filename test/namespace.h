
/// A namespace to test.
namespace TestNamespace
{

/// A variable inside a namespace.
int variableX;

/// A function inside a namespace.
void function( int x, double y );

/// A class inside a namespace.
class TestClass
{
public:
    /// Constructor with default
    TestClass( void ) = default;

    /// Copy constructor with default
    TestClass( const TestClass &copy ) = default;

    /// Move constructor with default
    TestClass( TestClass &&move ) = default;
};

}
